"""Frame extraction through ffmpeg, for the formats AVFoundation will not open.

Matroska, WebM and WMV all land here.
"""

import shutil
import subprocess
from pathlib import Path

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


class FFmpegError(Exception):
    """Raised when ffmpeg is unavailable, or fails on a file."""


def is_available() -> bool:
    """Report whether both ffmpeg and ffprobe are on PATH."""
    return all(shutil.which(name) is not None for name in (FFMPEG, FFPROBE))


def probe_duration(video: Path) -> float:
    """Return the duration of `video` in seconds."""
    result = _run(
        [
            FFPROBE,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video),
        ],
        video,
    )
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        raise FFmpegError(f"could not read a duration from {video.name}") from None
    if duration <= 0:
        raise FFmpegError(f"{video.name} reports a duration of {duration}s")
    return duration


def extract_frame(video: Path, seconds: float, destination: Path, *, size: int) -> Path:
    """Write the frame at `seconds` to `destination` as a square PNG of `size` pixels.

    The frame keeps its own proportions and the remaining space is left transparent;
    see the note in `_avfoundation._write_padded_png` for why the canvas is square.
    """
    _run(
        [
            FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{seconds:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-vf",
            f"scale=w={size}:h={size}:force_original_aspect_ratio=decrease,"
            f"pad={size}:{size}:(ow-iw)/2:(oh-ih)/2:color=black@0",
            # PNG defaults to rgb24, which would turn the transparent padding solid black.
            "-pix_fmt",
            "rgba",
            str(destination),
        ],
        video,
    )
    if not destination.exists() or destination.stat().st_size == 0:
        raise FFmpegError(f"no frame at {seconds:.2f}s in {video.name}")
    return destination


def _run(command: list[str], video: Path) -> subprocess.CompletedProcess[str]:
    if not is_available():
        raise FFmpegError(
            f"{video.name} needs ffmpeg, which is not installed "
            "(`brew install ffmpeg`); macOS cannot decode this format on its own"
        )
    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except OSError as error:  # pragma: no cover - only when ffmpeg vanishes mid-run
        raise FFmpegError(f"could not run {command[0]}: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        raise FFmpegError(f"{command[0]} failed on {video.name}: {detail[-1] if detail else ''}")
    return result
