"""Command line interface."""

import contextlib
import os
from collections import Counter
from pathlib import Path
from typing import Annotated

import typer

from .adjust import FileResult, Status, run_batch
from .discovery import DEFAULT_EXTENSIONS, collect_videos, parse_extensions
from .frames import DEFAULT_ICON_SIZE
from .offsets import InvalidOffsetError, Offset, parse_offset

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help=(
        "Set the Finder thumbnail of every video in a directory to the frame at a "
        "chosen offset.\n\n"
        "macOS cannot be told which frame QuickLook should use, so this applies a "
        "custom file icon instead. Use --clear to undo it."
    ),
)


@app.command()
def main(
    targets: Annotated[
        list[Path],
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=True,
            readable=True,
            metavar="TARGET...",
            help="Directories of videos, or video files. Shell globs such as *.mp4 work.",
        ),
    ],
    offset: Annotated[
        str | None,
        typer.Option(
            "--offset",
            "-o",
            help="Where to take the frame from: seconds (10, 90s), a clock time "
            "(1:30, 1:00:30) or a percentage of the duration (25%).",
        ),
    ] = None,
    clear: Annotated[
        bool,
        typer.Option("--clear", help="Remove custom icons, restoring Finder's own thumbnails."),
    ] = False,
    recursive: Annotated[
        bool,
        typer.Option(
            "--recursive", "-r", help="Descend into subdirectories. Ignored for a single file."
        ),
    ] = False,
    extensions: Annotated[
        str,
        typer.Option("--ext", help="Comma-separated video extensions to consider."),
    ] = ",".join(sorted(DEFAULT_EXTENSIONS)),
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Report what would change without touching anything.")
    ] = False,
    icon_size: Annotated[
        int,
        typer.Option(
            "--icon-size",
            min=16,
            max=2048,
            help="Pixel size of the square icon. Bigger is sharper at large icon "
            "sizes and costs more disk space in each file's resource fork.",
        ),
    ] = DEFAULT_ICON_SIZE,
    jobs: Annotated[
        int, typer.Option("--jobs", "-j", min=1, help="Number of videos to process in parallel.")
    ] = min(8, os.cpu_count() or 4),
) -> None:
    """Adjust the Finder thumbnails of the given videos."""
    wanted_offset = _resolve_mode(offset, clear=clear)

    videos = collect_videos(targets, parse_extensions(extensions), recursive=recursive)
    if not videos:
        typer.echo(f"No videos found in {', '.join(str(target) for target in targets)}")
        raise typer.Exit(0)

    results = run_batch(
        videos, offset=wanted_offset, dry_run=dry_run, jobs=jobs, icon_size=icon_size
    )
    _report(results, _display_base(videos))

    if not dry_run:
        _nudge_finder(results)

    if any(result.status.is_failure for result in results):
        raise typer.Exit(1)


def _resolve_mode(offset: str | None, *, clear: bool) -> Offset | None:
    """Validate the offset/clear pair and return the offset to apply, or None to clear."""
    if clear and offset is not None:
        raise typer.BadParameter("--clear cannot be combined with --offset")
    if not clear and offset is None:
        raise typer.BadParameter("give an --offset, or --clear to restore the defaults")
    if clear:
        return None
    try:
        return parse_offset(offset or "")
    except InvalidOffsetError as error:
        raise typer.BadParameter(str(error)) from error


def _display_base(videos: list[Path]) -> Path:
    """The directory names are shown relative to, so reports stay readable."""
    base = Path(os.path.commonpath([str(video) for video in videos]))
    return base if base.is_dir() else base.parent


def _report(results: list[FileResult], base: Path) -> None:
    for result in results:
        name = result.path.relative_to(base)
        detail = f" ({result.detail})" if result.detail else ""
        line = f"{result.status.value:>12}  {name}{detail}"
        typer.secho(line, err=result.status.is_failure, fg=_colour(result.status))

    tally = Counter(result.status.value for result in results)
    summary = ", ".join(f"{count} {status}" for status, count in sorted(tally.items()))
    typer.echo(f"\n{len(results)} file(s): {summary}")


def _colour(status: Status) -> str | None:
    match status:
        case Status.FAILED:
            return typer.colors.RED
        case Status.UPDATED | Status.CLEARED:
            return typer.colors.GREEN
        case Status.SKIPPED:
            return typer.colors.YELLOW
        case _:
            return None


def _nudge_finder(results: list[FileResult]) -> None:
    """Touch the directories we changed so Finder re-reads their icons."""
    changed = {
        result.path.parent
        for result in results
        if result.status in (Status.UPDATED, Status.CLEARED)
    }
    for parent in changed:
        # A read-only parent is not worth failing the run over.
        with contextlib.suppress(OSError):
            parent.touch()


if __name__ == "__main__":  # pragma: no cover
    app()
