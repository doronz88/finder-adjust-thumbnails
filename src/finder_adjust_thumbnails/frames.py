"""Reading video durations and extracting single frames.

macOS decodes most video itself, so AVFoundation goes first: no external binary, and
rotated footage is handled correctly. ffmpeg is the last resort, for the formats
QuickTime never learned — Matroska, WebM, WMV — and is only needed if you own some.
"""

from dataclasses import dataclass
from pathlib import Path

from . import _avfoundation, _ffmpeg

# Finder's icon slider tops out at 512pt, so a 512px icon covers every view without
# storing pixels nobody sees. Each icon lives in the video's resource fork, and the
# cost is roughly quadratic in this number.
DEFAULT_ICON_SIZE = 512

MACOS = "macOS"
FFMPEG = "ffmpeg"


class FrameError(RuntimeError):
    """Raised when a video cannot be probed or a frame cannot be extracted."""


@dataclass(frozen=True, slots=True)
class Engine:
    """Whichever decoder can read a given file."""

    name: str

    @property
    def is_fallback(self) -> bool:
        return self.name == FFMPEG

    def probe_duration(self, video: Path) -> float:
        """Return the duration of `video` in seconds."""
        if self.name == MACOS:
            try:
                return _avfoundation.probe_duration(video)
            except _avfoundation.UnsupportedByAVFoundation:
                pass  # macOS opened the file but cannot tell us this; let ffmpeg try
        return _run_ffmpeg(_ffmpeg.probe_duration, video)

    def extract_frame(self, video: Path, seconds: float, destination: Path, size: int) -> Path:
        """Write the frame at `seconds` to `destination` as a square PNG of `size` pixels."""
        if self.name == MACOS:
            try:
                return _avfoundation.extract_frame(video, seconds, destination, size=size)
            except _avfoundation.UnsupportedByAVFoundation:
                pass
        return _run_ffmpeg(_ffmpeg.extract_frame, video, seconds, destination, size=size)


def engine_for(video: Path) -> Engine:
    """Pick the decoder for `video`: macOS where it can, ffmpeg where it cannot."""
    return Engine(MACOS if _avfoundation.can_read(video) else FFMPEG)


def probe_duration(video: Path) -> float:
    """Return the duration of `video` in seconds."""
    return engine_for(video).probe_duration(video)


def extract_frame(
    video: Path, seconds: float, destination: Path, *, size: int = DEFAULT_ICON_SIZE
) -> Path:
    """Extract the frame at `seconds` from `video` as a square PNG of `size` pixels.

    File icons are square and macOS stretches whatever it is given to fill that square,
    so the frame is centred at its own proportions with transparent padding around it.
    """
    return engine_for(video).extract_frame(video, seconds, destination, size)


def _run_ffmpeg(operation, video: Path, *args, **kwargs):
    try:
        return operation(video, *args, **kwargs)
    except _ffmpeg.FFmpegError as error:
        raise FrameError(str(error)) from error
