"""Finding the video files a run should operate on."""

from collections.abc import Iterable
from pathlib import Path

DEFAULT_EXTENSIONS = frozenset({"mp4", "mov", "m4v", "mkv", "avi", "webm", "wmv"})


def parse_extensions(text: str) -> set[str]:
    """Parse a comma-separated extension list such as `mp4,.mkv,MOV`."""
    return {part.strip().lstrip(".").lower() for part in text.split(",") if part.strip()}


def find_videos(directory: Path, extensions: Iterable[str], *, recursive: bool) -> list[Path]:
    """Return the video files directly in `directory`, or beneath it when `recursive`."""
    wanted = {ext.lower() for ext in extensions}
    paths = directory.rglob("*") if recursive else directory.glob("*")
    return sorted(
        (
            path
            for path in paths
            if path.is_file()
            and not path.name.startswith(".")
            and path.suffix.lstrip(".").lower() in wanted
        ),
        key=lambda path: (path.parent.as_posix(), path.name),
    )


def collect_videos(
    targets: Iterable[Path], extensions: Iterable[str], *, recursive: bool
) -> list[Path]:
    """Return the videos to process, from any mix of files and directories.

    A file named explicitly is always used, whatever its extension — naming it is a
    clearer statement of intent than the extension filter. A video reached more than
    once, as a shell glob overlapping a directory will do, is only returned once.
    """
    found: dict[Path, None] = {}
    for target in targets:
        if target.is_file():
            found[target.resolve()] = None
        else:
            for video in find_videos(target, extensions, recursive=recursive):
                found[video.resolve()] = None
    return list(found)
