"""Which engine reads which file, and what happens when the fallback is unavailable."""

import shutil

import pytest
from conftest import colour_bounds, is_yellow

from finder_adjust_thumbnails import _avfoundation, _ffmpeg
from finder_adjust_thumbnails.frames import FrameError, extract_frame, probe_duration


def test_avfoundation_reads_an_mp4(sample_video):
    assert _avfoundation.can_read(sample_video)


@pytest.mark.parametrize("fixture", ["mkv_video"])
def test_avfoundation_cannot_read_matroska(fixture, request):
    assert not _avfoundation.can_read(request.getfixturevalue(fixture))


def test_a_file_that_is_not_a_video_is_not_readable(tmp_path):
    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"not a video")

    assert not _avfoundation.can_read(broken)


def test_an_mp4_never_reaches_ffmpeg(sample_video, tmp_path, monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("ffmpeg should not be used for a file AVFoundation can read")

    monkeypatch.setattr(_ffmpeg, "probe_duration", explode)
    monkeypatch.setattr(_ffmpeg, "extract_frame", explode)

    assert probe_duration(sample_video) == pytest.approx(5.0, abs=0.2)
    assert extract_frame(sample_video, 1.0, tmp_path / "frame.png", size=256).exists()


def test_matroska_falls_back_to_ffmpeg(mkv_video, tmp_path):
    assert probe_duration(mkv_video) == pytest.approx(5.0, abs=0.2)
    assert extract_frame(mkv_video, 1.0, tmp_path / "frame.png", size=256).exists()


def test_an_mp4_works_without_ffmpeg_installed(sample_video, tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    assert probe_duration(sample_video) > 0
    assert extract_frame(sample_video, 1.0, tmp_path / "frame.png", size=256).exists()


def test_matroska_without_ffmpeg_reports_what_is_missing(mkv_video, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    with pytest.raises(FrameError) as caught:
        probe_duration(mkv_video)

    assert "ffmpeg" in str(caught.value)
    assert mkv_video.name in str(caught.value)


def test_rotated_footage_comes_out_upright(rotated_video, tmp_path):
    """A 90 degree display rotation must be applied, or portrait clips land sideways."""
    frame = extract_frame(rotated_video, 1.0, tmp_path / "frame.png", size=512)

    width, height = colour_bounds(frame, is_yellow)
    assert width / height == pytest.approx(1.0, rel=0.15)


def test_rotated_footage_is_portrait_shaped(rotated_video, tmp_path):
    from conftest import opaque_bounds

    frame = extract_frame(rotated_video, 1.0, tmp_path / "frame.png", size=512)

    width, height = opaque_bounds(frame)
    assert width / height == pytest.approx(360 / 640, rel=0.05)
