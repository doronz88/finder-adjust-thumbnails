"""Tests for the macOS custom icon layer.

The custom icon flag lives in the `com.apple.FinderInfo` extended attribute, so these
tests read it back with the `xattr` tool rather than trusting our own reader.
"""

import subprocess

import pytest

from finder_adjust_thumbnails.icons import IconError, clear_icon, has_custom_icon, set_icon

HAS_CUSTOM_ICON_FLAG = 0x04  # high byte of the Finder flags word, at offset 8


def finder_info_says_custom_icon(path) -> bool:
    result = subprocess.run(
        ["xattr", "-px", "com.apple.FinderInfo", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    finder_info = bytes.fromhex(result.stdout.replace("\n", "").replace(" ", ""))
    return bool(finder_info[8] & HAS_CUSTOM_ICON_FLAG)


@pytest.fixture
def target(tmp_path):
    path = tmp_path / "movie.mp4"
    path.write_bytes(b"pretend this is a video")
    return path


def test_a_fresh_file_has_no_custom_icon(target):
    assert not finder_info_says_custom_icon(target)
    assert not has_custom_icon(target)


def test_setting_an_icon_marks_the_file_as_having_a_custom_icon(target, sample_image):
    set_icon(target, sample_image)

    assert finder_info_says_custom_icon(target)
    assert has_custom_icon(target)


def test_clearing_removes_the_custom_icon(target, sample_image):
    set_icon(target, sample_image)

    clear_icon(target)

    assert not finder_info_says_custom_icon(target)
    assert not has_custom_icon(target)


def test_clearing_a_file_without_an_icon_is_harmless(target):
    clear_icon(target)

    assert not has_custom_icon(target)


def test_setting_an_unreadable_image_raises(target, tmp_path):
    not_an_image = tmp_path / "junk.png"
    not_an_image.write_bytes(b"not a png")

    with pytest.raises(IconError):
        set_icon(target, not_an_image)
