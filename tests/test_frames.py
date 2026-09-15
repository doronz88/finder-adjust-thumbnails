import pytest

from finder_adjust_thumbnails.frames import FrameError, extract_frame, probe_duration


def test_probe_duration_reads_the_length_of_a_real_video(sample_video):
    assert probe_duration(sample_video) == pytest.approx(5.0, abs=0.2)


def test_probe_duration_rejects_a_file_that_is_not_a_video(tmp_path):
    not_a_video = tmp_path / "broken.mp4"
    not_a_video.write_bytes(b"this is not a video")

    with pytest.raises(FrameError):
        probe_duration(not_a_video)


def test_extract_frame_writes_an_image(sample_video, tmp_path):
    frame = extract_frame(sample_video, 1.0, tmp_path / "frame.png")

    assert frame.exists()
    assert frame.read_bytes().startswith(b"\x89PNG")


def test_frames_from_different_offsets_differ(sample_video, tmp_path):
    early = extract_frame(sample_video, 0.0, tmp_path / "early.png").read_bytes()
    late = extract_frame(sample_video, 4.0, tmp_path / "late.png").read_bytes()

    assert early != late


def test_extract_frame_past_the_end_raises(sample_video, tmp_path):
    with pytest.raises(FrameError):
        extract_frame(sample_video, 99.0, tmp_path / "frame.png")


def test_extracted_icon_is_square(wide_video, tmp_path):
    from AppKit import NSBitmapImageRep

    frame = extract_frame(wide_video, 1.0, tmp_path / "frame.png", size=512)

    rep = NSBitmapImageRep.imageRepWithContentsOfFile_(str(frame))
    assert (rep.pixelsWide(), rep.pixelsHigh()) == (512, 512)


def test_a_wide_frame_keeps_its_proportions(wide_video, tmp_path):
    """A 16:9 frame must be letterboxed into the square icon, never stretched to fill."""
    from conftest import opaque_bounds

    frame = extract_frame(wide_video, 1.0, tmp_path / "frame.png", size=512)

    width, height = opaque_bounds(frame)
    assert width / height == pytest.approx(16 / 9, rel=0.05)


def test_a_square_in_the_video_stays_square_in_the_icon(wide_video, tmp_path):
    from conftest import colour_bounds, is_yellow

    frame = extract_frame(wide_video, 1.0, tmp_path / "frame.png", size=512)

    width, height = colour_bounds(frame, is_yellow)
    assert width / height == pytest.approx(1.0, rel=0.1)


def test_the_icon_is_capped_at_the_requested_size(wide_video, tmp_path):
    from AppKit import NSBitmapImageRep

    frame = extract_frame(wide_video, 1.0, tmp_path / "frame.png", size=256)

    rep = NSBitmapImageRep.imageRepWithContentsOfFile_(str(frame))
    assert (rep.pixelsWide(), rep.pixelsHigh()) == (256, 256)


def test_a_smaller_icon_takes_less_space(wide_video, tmp_path):
    small = extract_frame(wide_video, 1.0, tmp_path / "small.png", size=256)
    large = extract_frame(wide_video, 1.0, tmp_path / "large.png", size=1024)

    assert small.stat().st_size < large.stat().st_size
