#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Helpers for normalising downloaded container formats."""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover

__all__ = ["ensure_flac_container"]


@dataclass(frozen=True)
class _CoverArt:
    """Simple structure for cover artwork extracted from MP4 containers."""

    data: bytes
    mime: str
    width: int = 0
    height: int = 0
    depth: int = 0
    colors: int = 0


def ensure_flac_container(file_path: str | Path) -> bool:
    """Ensure ``file_path`` is a genuine FLAC container.

    TIDAL occasionally serves FLAC audio streams wrapped in an MP4/M4A
    container.  This helper re-muxes such files into a standalone FLAC file so
    the rest of the tagging pipeline can operate normally.

    Returns ``True`` when a conversion took place, ``False`` otherwise.
    """

    path = Path(file_path)
    if path.suffix.lower() != ".flac" or not path.exists():
        return False

    if _looks_like_flac(path):
        return False

    if not _looks_like_mp4(path):
        return False

    if shutil.which("ffmpeg") is None:
        logging.warning(
            "Skipping FLAC container extraction because 'ffmpeg' is not available: %s",
            path,
        )
        return False

    cover_art = _extract_mp4_cover_art(path)

    logging.info("Extracting FLAC stream from MP4 container: %s", path)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()

    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(path),
        "-map",
        "0:a:0",
        "-c:a",
        "copy",
        str(tmp_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:  # pragma: no cover - best effort
        stderr = exc.stderr.decode(errors="ignore") if exc.stderr else ""
        logging.error(
            "Failed to extract FLAC stream from %s: %s", path, stderr.strip() or exc
        )
        if tmp_path.exists():
            tmp_path.unlink()
        return False

    path.unlink()
    tmp_path.replace(path)

    if cover_art:
        _reattach_cover_art(path, cover_art)
    return True


def _looks_like_flac(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            header = handle.read(4)
    except OSError:
        return False
    return header.startswith(b"fLaC")


def _looks_like_mp4(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            header = handle.read(12)
    except OSError:
        return False

    if len(header) < 8:
        return False
    return header[4:8] == b"ftyp"


def _probe_cover_art(data: bytes, mime: str) -> tuple[int, int, int, int]:
    if mime == "image/jpeg":
        return _probe_jpeg_dimensions(data)
    if mime == "image/png":
        return _probe_png_dimensions(data)
    if mime == "image/bmp":
        return _probe_bmp_dimensions(data)
    return 0, 0, 0, 0


def _probe_jpeg_dimensions(data: bytes) -> tuple[int, int, int, int]:
    i = 2
    size = len(data)
    while i + 9 < size:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        i += 2
        if marker in (0xD8, 0xD9, 0x01) or 0xD0 <= marker <= 0xD7:
            continue
        if i + 2 > size:
            break
        length = (data[i] << 8) + data[i + 1]
        if length < 2 or i + length > size:
            break
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            if length < 7:
                break
            depth = data[i + 2]
            height = (data[i + 3] << 8) + data[i + 4]
            width = (data[i + 5] << 8) + data[i + 6]
            return width, height, depth, 0
        i += length
    return 0, 0, 0, 0


def _probe_png_dimensions(data: bytes) -> tuple[int, int, int, int]:
    if len(data) < 33 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return 0, 0, 0, 0
    if data[12:16] != b"IHDR":
        return 0, 0, 0, 0
    width = int.from_bytes(data[16:20], "big", signed=False)
    height = int.from_bytes(data[20:24], "big", signed=False)
    bit_depth = data[24]
    color_type = data[25]
    channels = {0: 1, 2: 3, 3: 2, 4: 4, 6: 4}.get(color_type, 0)
    depth = bit_depth * channels if channels else bit_depth
    return width, height, depth, 0


def _probe_bmp_dimensions(data: bytes) -> tuple[int, int, int, int]:
    if len(data) < 30 or not data.startswith(b"BM"):
        return 0, 0, 0, 0
    header_size = int.from_bytes(data[14:18], "little", signed=False)
    if header_size < 12:
        return 0, 0, 0, 0
    width = int.from_bytes(data[18:22], "little", signed=True)
    height_raw = int.from_bytes(data[22:26], "little", signed=True)
    height = abs(height_raw)
    depth = 0
    colors = 0
    if header_size >= 24 and len(data) >= 30:
        depth = int.from_bytes(data[28:30], "little", signed=False)
    if header_size >= 32 and len(data) >= 36:
        colors = int.from_bytes(data[32:36], "little", signed=False)
    return max(width, 0), max(height, 0), depth, colors


def _extract_mp4_cover_art(path: Path) -> Optional[_CoverArt]:
    """Return embedded cover art information from an MP4 container."""
    try:
        mp4 = MP4(str(path))
    except Exception:  # pragma: no cover - best effort depending on mutagen
        return None

    if not mp4.tags:
        return None

    covers = mp4.tags.get("covr")
    if not covers:
        return None

    cover = covers[0]
    mime = "image/jpeg"
    if isinstance(cover, MP4Cover):
        if cover.imageformat == MP4Cover.FORMAT_PNG:
            mime = "image/png"
        elif cover.imageformat == MP4Cover.FORMAT_BMP:
            mime = "image/bmp"
        data = bytes(cover)
    else:
        data = bytes(cover)

    if not data:
        return None

    width, height, depth, colors = _probe_cover_art(data, mime)
    return _CoverArt(data=data, mime=mime, width=width, height=height, depth=depth, colors=colors)


def _reattach_cover_art(path: Path, cover_art: _CoverArt) -> None:
    """Attach extracted cover art to the FLAC file if possible."""
    try:
        flac = FLAC(str(path))
    except Exception:  # pragma: no cover - best effort depending on mutagen
        return

    picture = Picture()
    picture.data = cover_art.data
    picture.type = 3  # front cover
    picture.mime = cover_art.mime
    picture.desc = "Front Cover"
    if cover_art.width:
        picture.width = cover_art.width
    if cover_art.height:
        picture.height = cover_art.height
    if cover_art.depth:
        picture.depth = cover_art.depth
    if cover_art.colors:
        picture.colors = cover_art.colors

    try:
        flac.clear_pictures()
        flac.add_picture(picture)
        flac.save()
    except Exception:  # pragma: no cover - best effort depending on mutagen
        logging.debug("Failed to reattach cover art to %s", path, exc_info=True)

