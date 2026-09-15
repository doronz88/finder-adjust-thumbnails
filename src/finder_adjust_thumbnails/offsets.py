"""Parsing and resolution of the thumbnail offset."""

import re
from dataclasses import dataclass

# Keep the extracted frame this far away from the very end of the video; seeking to
# exactly the duration yields no frame at all.
END_MARGIN_SECONDS = 0.1

_CLOCK_RE = re.compile(r"^(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)$")
_SECONDS_RE = re.compile(r"^(\d+(?:\.\d+)?)s?$")
_PERCENT_RE = re.compile(r"^(\d+(?:\.\d+)?)%$")


class InvalidOffsetError(ValueError):
    """Raised when an offset string cannot be understood."""


@dataclass(frozen=True, slots=True)
class Offset:
    """An offset into a video, either absolute or relative to its duration."""

    value: float
    is_percent: bool

    def resolve(self, duration: float) -> float:
        """Return the absolute seconds this offset points at, inside a video of `duration`."""
        seconds = duration * self.value / 100 if self.is_percent else self.value
        return max(0.0, min(seconds, duration - END_MARGIN_SECONDS))

    def __str__(self) -> str:
        return f"{self.value:g}%" if self.is_percent else f"{self.value:g}s"


def parse_offset(text: str) -> Offset:
    """Parse an offset such as `10`, `90s`, `1:30`, `1:00:30` or `25%`."""
    text = text.strip()

    if match := _PERCENT_RE.match(text):
        percent = float(match.group(1))
        if percent > 100:
            raise InvalidOffsetError(f"percentage out of range: {text!r}")
        return Offset(percent, is_percent=True)

    if match := _SECONDS_RE.match(text):
        return Offset(float(match.group(1)), is_percent=False)

    if match := _CLOCK_RE.match(text):
        hours, minutes, seconds = match.groups()
        return Offset(int(hours or 0) * 3600 + int(minutes) * 60 + float(seconds), is_percent=False)

    raise InvalidOffsetError(
        f"cannot parse offset {text!r}; expected seconds (10, 90s), a clock time "
        "(1:30, 1:00:30) or a percentage (25%)"
    )
