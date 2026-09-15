import os
import shutil

import pytest
from typer.testing import CliRunner

from finder_adjust_thumbnails.cli import app
from finder_adjust_thumbnails.icons import has_custom_icon

# GitHub Actions makes Rich colourise Typer's error boxes, which splices ANSI codes
# through option names like "--clear". Tests assert on what a user reads, so colour is
# turned off for them.
runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb", "FORCE_COLOR": ""})


@pytest.fixture
def library(sample_video, tmp_path):
    """A directory with two videos, a nested video and an unrelated file."""
    for name in ("one.mp4", "two.mov", "sub/three.mp4"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(sample_video, path)
    (tmp_path / "notes.txt").write_text("hello")
    return tmp_path


def test_sets_icons_on_every_video_in_the_directory(library):
    result = runner.invoke(app, [str(library), "--offset", "2"])

    assert result.exit_code == 0
    assert has_custom_icon(library / "one.mp4")
    assert has_custom_icon(library / "two.mov")


def test_leaves_subdirectories_alone_without_recursive(library):
    runner.invoke(app, [str(library), "--offset", "2"])

    assert not has_custom_icon(library / "sub" / "three.mp4")


def test_recursive_reaches_nested_videos(library):
    result = runner.invoke(app, [str(library), "--offset", "2", "--recursive"])

    assert result.exit_code == 0
    assert has_custom_icon(library / "sub" / "three.mp4")


def test_extension_filter_limits_the_files_touched(library):
    runner.invoke(app, [str(library), "--offset", "2", "--ext", "mov"])

    assert has_custom_icon(library / "two.mov")
    assert not has_custom_icon(library / "one.mp4")


def test_dry_run_reports_without_changing_anything(library):
    result = runner.invoke(app, [str(library), "--offset", "2", "--dry-run"])

    assert result.exit_code == 0
    assert "would update" in result.output
    assert not has_custom_icon(library / "one.mp4")


def test_clear_restores_the_default_thumbnails(library):
    runner.invoke(app, [str(library), "--offset", "2"])

    result = runner.invoke(app, [str(library), "--clear"])

    assert result.exit_code == 0
    assert not has_custom_icon(library / "one.mp4")


def test_offset_and_clear_together_are_rejected(library):
    result = runner.invoke(app, [str(library), "--offset", "2", "--clear"])

    assert result.exit_code == 2
    assert "--clear" in result.output


def test_neither_offset_nor_clear_is_rejected(library):
    result = runner.invoke(app, [str(library)])

    assert result.exit_code == 2
    assert "--offset" in result.output


def test_an_unparsable_offset_is_reported_clearly(library):
    result = runner.invoke(app, [str(library), "--offset", "banana"])

    assert result.exit_code == 2
    assert "banana" in result.output


def test_a_missing_directory_is_rejected(tmp_path):
    result = runner.invoke(app, [str(tmp_path / "nope"), "--offset", "2"])

    assert result.exit_code == 2


def test_a_directory_without_videos_says_so(tmp_path):
    result = runner.invoke(app, [str(tmp_path), "--offset", "2"])

    assert result.exit_code == 0
    assert "no videos" in result.output.lower()


def test_exit_code_is_one_when_a_file_fails(library):
    (library / "broken.mp4").write_bytes(b"not a video")

    result = runner.invoke(app, [str(library), "--offset", "2"])

    assert result.exit_code == 1
    assert "broken.mp4" in result.output


def test_ordinary_videos_do_not_need_ffmpeg_at_all(library, monkeypatch):
    """macOS decodes mp4/mov itself, so a library of them works with no ffmpeg installed."""
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    result = runner.invoke(app, [str(library), "--offset", "2"])

    assert result.exit_code == 0
    assert has_custom_icon(library / "one.mp4")


def test_a_format_macos_cannot_read_says_it_needs_ffmpeg(library, mkv_video, monkeypatch):
    shutil.copy(mkv_video, library / "odd.mkv")
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    result = runner.invoke(app, [str(library), "--offset", "2"])

    assert result.exit_code == 1
    assert "ffmpeg" in result.output
    assert "odd.mkv" in result.output
    # The files macOS can read are still done.
    assert has_custom_icon(library / "one.mp4")


def test_the_report_names_the_fallback_when_it_is_used(library, mkv_video):
    shutil.copy(mkv_video, library / "odd.mkv")

    result = runner.invoke(app, [str(library), "--offset", "2"])

    assert result.exit_code == 0
    odd_line = next(line for line in result.output.splitlines() if "odd.mkv" in line)
    one_line = next(line for line in result.output.splitlines() if "one.mp4" in line)
    assert "ffmpeg" in odd_line
    assert "ffmpeg" not in one_line


def test_the_containing_directory_is_touched_so_finder_notices(library):
    os.utime(library, (0, 0))

    runner.invoke(app, [str(library), "--offset", "2"])

    assert library.stat().st_mtime > 0


def test_a_single_file_can_be_given_instead_of_a_directory(library):
    result = runner.invoke(app, [str(library / "one.mp4"), "--offset", "2"])

    assert result.exit_code == 0
    assert has_custom_icon(library / "one.mp4")
    assert not has_custom_icon(library / "two.mov")


def test_a_single_file_reports_its_name(library):
    result = runner.invoke(app, [str(library / "one.mp4"), "--offset", "2"])

    assert result.exit_code == 0
    assert "updated" in result.output
    assert "one.mp4" in result.output


def test_a_single_file_can_be_cleared(library):
    runner.invoke(app, [str(library / "one.mp4"), "--offset", "2"])

    result = runner.invoke(app, [str(library / "one.mp4"), "--clear"])

    assert result.exit_code == 0
    assert not has_custom_icon(library / "one.mp4")


def test_icon_size_option_produces_a_smaller_resource_fork(library):
    from conftest import resource_fork_size

    runner.invoke(app, [str(library / "one.mp4"), "--offset", "2", "--icon-size", "1024"])
    large = resource_fork_size(library / "one.mp4")

    runner.invoke(app, [str(library / "one.mp4"), "--offset", "2", "--icon-size", "256"])
    small = resource_fork_size(library / "one.mp4")

    assert 0 < small < large


def test_an_absurd_icon_size_is_rejected(library):
    result = runner.invoke(app, [str(library), "--offset", "2", "--icon-size", "99999"])

    assert result.exit_code == 2
    assert "range" in result.output.lower()
    assert not has_custom_icon(library / "one.mp4")
