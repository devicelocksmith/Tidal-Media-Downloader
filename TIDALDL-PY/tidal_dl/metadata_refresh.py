#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Utilities for refreshing FLAC metadata using the TIDAL catalogue."""

from __future__ import annotations

import logging
import os
import random
import re
import time
from pathlib import Path
from typing import Iterable, Optional, Sequence

from mutagen import MutagenError
from mutagen.flac import FLAC

from .enums import Type
from .model import Album, Artist, Track
from .printf import Printf
from .settings import SETTINGS
from .tidal import TIDAL_API

try:
    from .download import _update_flac_metadata  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - best effort fallback
    _update_flac_metadata = None  # type: ignore[assignment]


_SEARCH_DELAY_ARMED = False


def _should_delay_search() -> bool:
    try:
        return bool(getattr(SETTINGS, "metadataRefreshDelay", False))
    except Exception:
        return False


def _random_delay_seconds() -> float:
    return random.randint(500, 5000) / 1000.0


def _sleep_before_search() -> None:
    if not _should_delay_search():
        return
    if not _SEARCH_DELAY_ARMED:
        return
    delay = _random_delay_seconds()
    logging.debug(
        "Waiting %.3f seconds before next metadata refresh search", delay
    )
    time.sleep(delay)


def _mark_search_request() -> None:
    global _SEARCH_DELAY_ARMED
    if _should_delay_search():
        _SEARCH_DELAY_ARMED = True
    else:
        _SEARCH_DELAY_ARMED = False


def _normalise(text: Optional[str]) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _iter_artist_names(source: Optional[Sequence[Artist] | Artist]) -> Iterable[str]:
    if source is None:
        return
    if isinstance(source, (list, tuple)):
        iterable = source
    else:
        iterable = [source]
    for artist in iterable:
        name = getattr(artist, "name", None)
        if name:
            yield str(name)


def _split_existing_artists(raw: Optional[Sequence[str] | str]) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        values = [raw]
    else:
        values = list(raw)
    artists: list[str] = []
    for entry in values:
        if not entry:
            continue
        parts = re.split(r"[,/&]", str(entry))
        for part in parts:
            name = part.strip()
            if name:
                artists.append(name)
    return artists


def _format_track_title(track: Track) -> str:
    base_title = getattr(track, "title", "") or ""
    version = getattr(track, "version", None)
    if version:
        return f"{base_title} ({version})"
    return base_title


def _candidate_artist_names(track: Track) -> list[str]:
    names = list(_iter_artist_names(getattr(track, "artists", None)) or [])
    if not names:
        primary = getattr(track, "artist", None)
        name = getattr(primary, "name", None)
        if name:
            names.append(str(name))
    return names


def _album_artist_names(album: Optional[Album]) -> list[str]:
    if album is None:
        return []
    return list(_iter_artist_names(getattr(album, "artists", None)) or [])


def _set_tag(audio: FLAC, key: str, values: Sequence[str] | str | None) -> bool:
    if values is None:
        return False
    if isinstance(values, str):
        cleaned = [values] if values.strip() else []
    else:
        cleaned = [str(item).strip() for item in values if str(item).strip()]
    if not cleaned:
        return False
    existing = list(audio.get(key, []))
    if existing == cleaned:
        return False
    audio[key] = cleaned
    return True


def _set_numeric_tag(audio: FLAC, key: str, value: Optional[int]) -> bool:
    if value in (None, 0):
        return False
    text = str(value)
    if list(audio.get(key, [])) == [text]:
        return False
    audio[key] = [text]
    return True


def _extract_first_value(raw: Optional[Sequence[str] | str]) -> Optional[str]:
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        for entry in raw:
            if entry:
                text = str(entry).strip()
                if text:
                    return text
        return None
    text = str(raw).strip()
    return text or None


def _derive_rekordbox_rating(popularity: Optional[int]) -> Optional[int]:
    try:
        value = int(popularity)
    except (TypeError, ValueError):
        return None
    if value < 0:
        value = 0
    if value > 100:
        value = 100
    rating = int((value + 10) // 20)
    return max(0, min(5, rating))


def _set_popularity_tags(audio: FLAC, popularity: Optional[int]) -> bool:
    try:
        value = int(popularity)
    except (TypeError, ValueError):
        return False
    changed = False
    changed |= _set_tag(audio, "TIDAL_TRACK_POPULARITY", str(value))
    rating = _derive_rekordbox_rating(value)
    if rating is not None:
        changed |= _set_tag(audio, "RB_RATING", str(rating))
    return changed


def _extract_composers(contributors: Optional[dict]) -> list[str]:
    if not contributors:
        return []
    try:
        items = contributors.get("items")
        if not isinstance(items, list):
            return []
        names = [entry.get("name") for entry in items if entry.get("role") == "Composer"]
        return [str(name) for name in names if name]
    except AttributeError:
        return []


def _find_matching_track(
    candidates: Sequence[Track],
    title: str,
    album: str,
    artists: list[str],
) -> Optional[Track]:
    title_norm = _normalise(title)
    album_norm = _normalise(album)
    artist_norm = { _normalise(name) for name in artists }
    for track in candidates:
        candidate_title = _normalise(_format_track_title(track))
        candidate_album = _normalise(getattr(getattr(track, "album", None), "title", None))
        candidate_artists = {
            _normalise(name)
            for name in _candidate_artist_names(track)
            if name
        }
        if not candidate_artists:
            continue
        if (
            candidate_title == title_norm
            and candidate_album == album_norm
            and candidate_artists == artist_norm
        ):
            return track
    return None


def _apply_track_metadata(
    audio: FLAC,
    track: Track,
    album: Optional[Album],
    contributors: Optional[dict],
) -> bool:
    changed = False
    changed |= _set_tag(audio, "title", _format_track_title(track))
    if album is not None:
        changed |= _set_tag(audio, "album", getattr(album, "title", None))
    changed |= _set_tag(audio, "artist", ", ".join(_candidate_artist_names(track)))
    album_artists = _album_artist_names(album)
    if album_artists:
        changed |= _set_tag(audio, "albumartist", ", ".join(album_artists))
    changed |= _set_tag(audio, "copyright", getattr(track, "copyRight", None))
    changed |= _set_numeric_tag(audio, "tracknumber", getattr(track, "trackNumber", None))
    if album is not None and getattr(album, "numberOfTracks", None):
        changed |= _set_numeric_tag(audio, "tracktotal", getattr(album, "numberOfTracks", None))
    changed |= _set_numeric_tag(audio, "discnumber", getattr(track, "volumeNumber", None))
    if album is not None and getattr(album, "numberOfVolumes", None):
        changed |= _set_numeric_tag(audio, "disctotal", getattr(album, "numberOfVolumes", None))
    if album is not None:
        changed |= _set_tag(audio, "date", getattr(album, "releaseDate", None))
    composers = _extract_composers(contributors)
    if composers:
        changed |= _set_tag(audio, "composer", ", ".join(composers))
    changed |= _set_tag(audio, "isrc", getattr(track, "isrc", None))
    return changed


def refresh_metadata_for_directory(target_directory: str) -> None:
    """Refresh metadata for FLAC files located under ``target_directory``."""

    target_path = Path(os.path.expanduser(target_directory)).resolve()
    if not target_path.exists():
        Printf.err(f"Target directory does not exist: {target_path}")
        return
    if not target_path.is_dir():
        Printf.err(f"Target path is not a directory: {target_path}")
        return

    flac_files = sorted(target_path.rglob("*.flac"))
    if not flac_files:
        Printf.info(f"No FLAC files found under {target_path}")
        return

    Printf.info(f"Scanning {len(flac_files)} FLAC file(s) under {target_path}")

    for flac_path in flac_files:
        try:
            audio = FLAC(str(flac_path))
        except (FileNotFoundError, MutagenError) as exc:
            Printf.err(f"Failed to open '{flac_path}': {exc}")
            continue

        existing_track_id = _extract_first_value(audio.get("TIDAL_TRACK_ID"))
        title = audio.get("title")
        title_value = title[0] if isinstance(title, list) and title else title
        album = audio.get("album")
        album_value = album[0] if isinstance(album, list) and album else album
        artist_values = _split_existing_artists(audio.get("artist"))

        if not title_value or not album_value or not artist_values:
            logging.debug(
                "Insufficient metadata to search for '%s' (title=%s, album=%s, artist=%s)",
                flac_path,
                title_value,
                album_value,
                artist_values,
            )
            continue

        query = f"{artist_values[0]} {title_value}" if artist_values else str(title_value)

        _sleep_before_search()
        try:
            search_result = TIDAL_API.search(query, Type.Track, limit=5)
            candidates = list(TIDAL_API.getSearchResultItems(search_result, Type.Track) or [])
        except Exception as exc:
            Printf.err(f"Search failed for '{flac_path.name}': {exc}")
            continue
        finally:
            _mark_search_request()

        match = _find_matching_track(candidates[:5], str(title_value), str(album_value), artist_values)
        if match is None:
            logging.debug("No matching TIDAL track found for %s", flac_path)
            continue

        try:
            track = TIDAL_API.getTrack(match.id)
        except Exception as exc:
            Printf.err(f"Failed to load track {match.id} for '{flac_path.name}': {exc}")
            continue

        popularity = getattr(track, "popularity", None)

        if existing_track_id:
            if str(match.id) != existing_track_id:
                logging.debug(
                    "Skipping %s due to TIDAL_TRACK_ID mismatch (expected %s, found %s)",
                    flac_path,
                    existing_track_id,
                    match.id,
                )
                continue

            try:
                popularity_changed = _set_popularity_tags(audio, popularity)
                if popularity_changed:
                    audio.save()
            except MutagenError as exc:
                Printf.err(f"Unable to update popularity tags for '{flac_path.name}': {exc}")
                continue

            Printf.success(
                f"Updated popularity for '{flac_path.name}' (TIDAL ID {match.id})"
            )
            continue

        album_obj: Optional[Album] = None
        album_id = getattr(getattr(track, "album", None), "id", None)
        if album_id:
            try:
                album_obj = TIDAL_API.getAlbum(album_id)
            except Exception as exc:
                logging.debug("Failed to load album %s for %s: %s", album_id, flac_path, exc)
                album_obj = getattr(track, "album", None)
        else:
            album_obj = getattr(track, "album", None)

        try:
            contributors = TIDAL_API.getTrackContributors(track.id)
        except Exception as exc:
            logging.debug("Unable to fetch contributors for %s: %s", track.id, exc)
            contributors = None

        try:
            changed = _apply_track_metadata(audio, track, album_obj, contributors)
            changed |= _set_popularity_tags(audio, popularity)
            if changed:
                audio.save()
        except MutagenError as exc:
            Printf.err(f"Unable to update FLAC tags for '{flac_path.name}': {exc}")
            continue

        extended_updated = False
        if _update_flac_metadata is not None:
            try:
                _update_flac_metadata(str(flac_path), track, album_obj, contributors, None)
                extended_updated = True
            except Exception as exc:
                logging.debug("Extended metadata update failed for %s: %s", flac_path, exc)
        if extended_updated:
            try:
                audio = FLAC(str(flac_path))
                if _set_popularity_tags(audio, popularity):
                    audio.save()
            except (MutagenError, FileNotFoundError) as exc:
                logging.debug("Post-update popularity refresh failed for %s: %s", flac_path, exc)
        else:
            try:
                audio = FLAC(str(flac_path))
            except (MutagenError, FileNotFoundError) as exc:
                logging.debug("Fallback tag update failed for %s: %s", flac_path, exc)
            else:
                audio["TIDAL_TRACK_ID"] = [str(track.id)]
                _set_popularity_tags(audio, popularity)
                try:
                    audio.save()
                except MutagenError as exc:
                    logging.debug("Failed to persist fallback metadata for %s: %s", flac_path, exc)

        Printf.success(f"Refreshed metadata for '{flac_path.name}' (TIDAL ID {track.id})")

