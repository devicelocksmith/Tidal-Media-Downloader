#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Utilities for normalising embedded FLAC cover artwork so that players
which rely on baseline JPEG front covers (e.g. Rekordbox) can correctly
recognise the album art.
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Iterable, Optional, Tuple

try:
    import av  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    av = None  # type: ignore

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    Image = None  # type: ignore

__all__ = ["ensure_flac_cover_art"]

_RE_TYPE3 = re.compile(r"^\s*type:\s+3\b", re.M)
_COVER_CANDIDATES = [
    "cover.jpg", "folder.jpg", "front.jpg",
    "Cover.jpg", "Folder.jpg", "Front.jpg",
    "cover.jpeg", "folder.jpeg", "front.jpeg",
    "cover.png", "folder.png", "front.png",
]

_DEPENDENCIES_AVAILABLE: bool | None = None
_FFMPEG_AVAILABLE: bool | None = None
_PYAV_AVAILABLE: bool | None = None


def _ffmpeg_ready() -> bool:
    global _FFMPEG_AVAILABLE
    if _FFMPEG_AVAILABLE is None:
        _FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
    return bool(_FFMPEG_AVAILABLE)


def _pyav_ready() -> bool:
    global _PYAV_AVAILABLE
    if _PYAV_AVAILABLE is None:
        _PYAV_AVAILABLE = av is not None and Image is not None
        if av is not None and Image is None:
            logging.debug(
                "PyAV is available but Pillow is missing; disabling PyAV cover normalisation."
            )
    return bool(_PYAV_AVAILABLE)


def _dependencies_ready() -> bool:
    """Return True when metaflac is available and a re-encode backend is present."""
    global _DEPENDENCIES_AVAILABLE
    if _DEPENDENCIES_AVAILABLE is None:
        metaflac_available = shutil.which("metaflac") is not None
        backend_available = _pyav_ready() or _ffmpeg_ready()
        _DEPENDENCIES_AVAILABLE = metaflac_available and backend_available
        if not metaflac_available:
            logging.debug("Skipping FLAC cover normalisation because 'metaflac' is missing.")
        elif not backend_available:
            logging.debug(
                "Skipping FLAC cover normalisation because neither PyAV nor 'ffmpeg' is available."
            )
    return bool(_DEPENDENCIES_AVAILABLE)


def _run(cmd: Iterable[str], *, check: bool = True, capture: bool = True):
    return subprocess.run(
        list(cmd),
        check=check,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
    )


def _is_already_good(flac_path: Path, max_px: int) -> bool:
    """Check if the FLAC already contains a baseline front cover image."""
    try:
        out = _run(["metaflac", "--list", "--block-type=PICTURE", str(flac_path)]).stdout
    except subprocess.CalledProcessError:
        return False

    blocks = out.split("METADATA_BLOCK_PICTURE")
    if len(blocks) != 2:
        return False

    block = blocks[1].splitlines()
    if not any("type:" in line and " 3 " in line for line in block):
        return False

    mime = next(
        (
            line.split(":", 1)[1].strip().lower()
            for line in block
            if line.strip().startswith("mime type:")
        ),
        "",
    )
    if mime != "image/jpeg":
        return False

    try:
        width_line = next(
            line for line in block if line.strip().startswith("width:")
        ).split()
        width = int(width_line[1][:-2])
        height = int(width_line[3][:-2])
    except (StopIteration, ValueError, IndexError):
        return False

    return max(width, height) <= max_px


def _has_metaflac_front_cover(flac_path: Path) -> bool:
    try:
        out = _run(["metaflac", "--list", "--block-type=PICTURE", str(flac_path)]).stdout
    except subprocess.CalledProcessError:
        return False
    return bool(_RE_TYPE3.search(out))


def _export_existing_picture(flac_path: Path, dest_file: Path) -> bool:
    try:
        _run(["metaflac", f"--export-picture-to={dest_file}", str(flac_path)])
    except subprocess.CalledProcessError:
        return False
    return dest_file.exists() and dest_file.stat().st_size > 0


def _find_folder_cover(start_dir: Path) -> Path | None:
    for name in _COVER_CANDIDATES:
        candidate = start_dir / name
        if candidate.exists() and candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def _reencode_with_pyav(src_img: Path, out_jpg: Path, max_px: int) -> Tuple[bool, str]:
    if not _pyav_ready():
        return False, "PyAV backend unavailable"

    assert av is not None  # for type-checkers
    try:
        with av.open(str(src_img)) as container:
            stream = next((s for s in container.streams if s.type == "video"), None)
            if stream is None:
                return False, "PyAV could not locate a video stream"
            frame = next(container.decode(stream), None)
            if frame is None:
                return False, "PyAV failed to decode the image frame"
            image = frame.to_image()
    except Exception as exc:  # pragma: no cover - PyAV raises many custom errors
        return False, f"PyAV error: {exc}"

    try:
        width, height = image.size
        scale = min(1.0, max_px / max(width, height))
        if scale < 1.0:
            new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            image = image.resize(new_size, Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
        image = image.convert("RGB")
        image.save(out_jpg, format="JPEG", quality=85, optimize=True, progressive=False)
    except Exception as exc:  # pragma: no cover - Pillow specific errors
        return False, f"PyAV/Pillow error: {exc}"

    return out_jpg.exists() and out_jpg.stat().st_size > 0, "PyAV"


def _reencode_with_ffmpeg(src_img: Path, out_jpg: Path, max_px: int) -> Tuple[bool, str]:
    if not _ffmpeg_ready():
        return False, "ffmpeg backend unavailable"

    scale = "scale='min({0},iw)':'min({0},ih)':force_original_aspect_ratio=decrease".format(max_px)
    cmd = [
        "ffmpeg", "-y", "-v", "error", "-i", str(src_img),
        "-vf", scale, "-q:v", "3", "-pix_fmt", "yuvj420p", str(out_jpg),
    ]
    try:
        _run(cmd)
    except subprocess.CalledProcessError as exc:
        return False, f"ffmpeg exited with code {exc.returncode}"
    return out_jpg.exists() and out_jpg.stat().st_size > 0, "ffmpeg"


def _reencode_to_baseline_jpeg(src_img: Path, out_jpg: Path, max_px: int) -> Tuple[bool, str]:
    """Re-encode a cover image to a baseline JPEG using PyAV when possible."""
    backends = (_reencode_with_pyav, _reencode_with_ffmpeg)
    last_reason = ""
    for backend in backends:
        success, detail = backend(src_img, out_jpg, max_px)
        if success:
            return True, detail
        last_reason = detail
    return False, last_reason or "No available backend"


def _import_front_cover(flac_path: Path, jpg_file: Path) -> None:
    _run(["metaflac", "--remove", "--block-type=PICTURE", str(flac_path)], capture=False)
    _run(["metaflac", f"--import-picture-from=3|image/jpeg|||{jpg_file}", str(flac_path)], capture=False)


def ensure_flac_cover_art(
    flac_path: str | Path,
    *,
    max_px: int = 1400,
    report: bool = False,
    fetch_cover: Optional[Callable[[Path], Optional[Path]]] = None,
) -> bool | Tuple[bool, str]:
    """Ensure the FLAC file contains a baseline JPEG front cover."""
    path = Path(flac_path)
    status_message = ""
    if path.suffix.lower() != ".flac" or not path.exists():
        status_message = "Target is not a FLAC file"
        return (False, status_message) if report else False

    if not _dependencies_ready():
        status_message = "Required cover art tools are unavailable"
        return (False, status_message) if report else False

    try:
        if _is_already_good(path, max_px):
            status_message = "Cover art already meets baseline JPEG requirements"
            return (True, status_message) if report else True
        if _has_metaflac_front_cover(path):
            status_message = "Cover art already present in FLAC metadata"
            return (True, status_message) if report else True

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            extracted = tmp_path / "extracted_art"
            baseline = tmp_path / "cover.jpg"

            have_art = _export_existing_picture(path, extracted)
            if not have_art:
                folder_cover = _find_folder_cover(path.parent)
                if folder_cover:
                    extracted = folder_cover
                    have_art = True

            if not have_art and fetch_cover is not None:
                try:
                    fetched = fetch_cover(tmp_path)
                except Exception:  # pragma: no cover - network/IO failures
                    logging.debug(
                        "Failed to obtain fallback cover art for %s", path, exc_info=True
                    )
                    fetched = None
                if fetched is not None and fetched.exists() and fetched.stat().st_size > 0:
                    extracted = fetched
                    have_art = True

            if not have_art:
                logging.debug("No cover art found for %s", path)
                status_message = "No cover art was found to embed"
                return (False, status_message) if report else False

            success, backend = _reencode_to_baseline_jpeg(extracted, baseline, max_px)
            if not success:
                logging.debug("Failed to re-encode cover art for %s", path)
                status_message = f"Failed to re-encode cover art ({backend})"
                return (False, status_message) if report else False

            _import_front_cover(path, baseline)
            status_message = f"Embedded baseline JPEG cover using {backend}"
            return (True, status_message) if report else True
    except FileNotFoundError:
        status_message = "metaflac executable was not found"
    except Exception:
        logging.debug("Failed to normalise cover art for %s", path, exc_info=True)
        status_message = "Unexpected error while normalising cover art"

    return (False, status_message) if report else False
