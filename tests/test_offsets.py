import pytest

from finder_adjust_thumbnails.offsets import InvalidOffsetError, parse_offset


@pytest.mark.parametrize(
    ("text", "duration", "expected"),
    [
        ("10", 60.0, 10.0),
        ("90s", 600.0, 90.0),
        ("1:30", 600.0, 90.0),
        ("1:00:30", 7200.0, 3630.0),
        ("2.5", 60.0, 2.5),
    ],
)
def test_absolute_offsets_resolve_to_seconds(text, duration, expected):
    assert parse_offset(text).resolve(duration) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("text", "duration", "expected"),
    [
        ("25%", 60.0, 15.0),
        ("0%", 60.0, 0.0),
        ("12.5%", 80.0, 10.0),
    ],
)
def test_percent_offsets_resolve_against_duration(text, duration, expected):
    assert parse_offset(text).resolve(duration) == pytest.approx(expected)


def test_offset_past_end_is_clamped_just_inside_the_video():
    assert parse_offset("30").resolve(10.0) == pytest.approx(9.9)


def test_hundred_percent_is_clamped_just_inside_the_video():
    assert parse_offset("100%").resolve(10.0) == pytest.approx(9.9)


def test_very_short_video_clamps_to_zero_rather_than_negative():
    assert parse_offset("5").resolve(0.05) == 0.0


@pytest.mark.parametrize("text", ["", "abc", "-5", "-10%", "110%", "1:2:3:4", "1:aa", "%"])
def test_invalid_offsets_are_rejected(text):
    with pytest.raises(InvalidOffsetError):
        parse_offset(text)
