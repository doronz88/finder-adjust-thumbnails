"""Turning an offset into a custom icon, one video at a time.

Frame extraction runs in parallel — it is the slow part, and it is just subprocesses.
Icon writing does not: AppKit's `setIcon:forFile:` takes an internal IconServices lock
and deadlocks when called from several threads at once, so every icon write happens
serially, on the thread that called in.
"""

import tempfile
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .frames import DEFAULT_ICON_SIZE, Engine, FrameError, engine_for
from .icons import IconError, clear_icon, has_custom_icon, set_icon
from .offsets import Offset


class Status(Enum):
    """What happened to a single file."""

    UPDATED = "updated"
    WOULD_UPDATE = "would update"
    CLEARED = "cleared"
    WOULD_CLEAR = "would clear"
    SKIPPED = "skipped"
    FAILED = "failed"

    @property
    def is_failure(self) -> bool:
        return self is Status.FAILED


@dataclass(frozen=True, slots=True)
class FileResult:
    """The outcome for one video."""

    path: Path
    status: Status
    detail: str = ""


@dataclass(frozen=True, slots=True)
class _Extracted:
    """A frame waiting to be written to a file's icon, or the failure that prevented it."""

    video: Path
    frame: Path | None
    detail: str


def apply_offset(
    video: Path, offset: Offset, *, dry_run: bool, icon_size: int = DEFAULT_ICON_SIZE
) -> FileResult:
    """Set `video`'s Finder icon to the frame at `offset`."""
    if dry_run:
        return _preview(video, offset)
    with tempfile.TemporaryDirectory() as workspace:
        extracted = _extract(video, offset, Path(workspace) / "frame.png", icon_size)
        return _write_icon(extracted)


def clear_thumbnail(video: Path, *, dry_run: bool) -> FileResult:
    """Remove `video`'s custom Finder icon, restoring the generated thumbnail."""
    try:
        if not has_custom_icon(video):
            return FileResult(video, Status.SKIPPED, "no custom icon")
        if dry_run:
            return FileResult(video, Status.WOULD_CLEAR)
        clear_icon(video)
        return FileResult(video, Status.CLEARED)
    except IconError as error:
        return FileResult(video, Status.FAILED, str(error))


def run_batch(
    videos: Sequence[Path],
    *,
    offset: Offset | None,
    dry_run: bool,
    jobs: int,
    icon_size: int = DEFAULT_ICON_SIZE,
) -> list[FileResult]:
    """Process every video, preserving input order. `offset=None` clears instead."""
    if not videos:
        return []
    if offset is None:
        return [clear_thumbnail(video, dry_run=dry_run) for video in videos]
    if dry_run:
        return _in_parallel(lambda video: _preview(video, offset), videos, jobs)

    with tempfile.TemporaryDirectory() as workspace:
        frames = [Path(workspace) / f"{index}.png" for index in range(len(videos))]
        extracted = _in_parallel(
            lambda pair: _extract(pair[0], offset, pair[1], icon_size),
            list(zip(videos, frames, strict=True)),
            jobs,
        )
        # Serial, and on this thread: concurrent AppKit icon writes deadlock.
        return [_write_icon(item) for item in extracted]


def _preview(video: Path, offset: Offset) -> FileResult:
    """Work out what would happen to `video`, without touching it."""
    engine = engine_for(video)
    try:
        seconds = offset.resolve(engine.probe_duration(video))
    except FrameError as error:
        return FileResult(video, Status.FAILED, str(error))
    return FileResult(video, Status.WOULD_UPDATE, _describe(seconds, engine))


def _extract(video: Path, offset: Offset, frame: Path, icon_size: int) -> _Extracted:
    """Pull the frame at `offset` out of `video`. Safe to run on a worker thread."""
    engine = engine_for(video)
    try:
        seconds = offset.resolve(engine.probe_duration(video))
        engine.extract_frame(video, seconds, frame, icon_size)
    except FrameError as error:
        return _Extracted(video, None, str(error))
    return _Extracted(video, frame, _describe(seconds, engine))


def _describe(seconds: float, engine: Engine) -> str:
    """Describe what was taken, noting the fallback decoder when it was needed."""
    detail = f"frame at {seconds:.2f}s"
    return f"{detail}, via {engine.name}" if engine.is_fallback else detail


def _write_icon(item: _Extracted) -> FileResult:
    """Apply an extracted frame as a file icon. Must not run on a worker thread."""
    if item.frame is None:
        return FileResult(item.video, Status.FAILED, item.detail)
    try:
        set_icon(item.video, item.frame)
    except IconError as error:
        return FileResult(item.video, Status.FAILED, str(error))
    return FileResult(item.video, Status.UPDATED, item.detail)


def _in_parallel[T, R](work: Callable[[T], R], items: Sequence[T], jobs: int) -> list[R]:
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        return list(pool.map(work, items))
