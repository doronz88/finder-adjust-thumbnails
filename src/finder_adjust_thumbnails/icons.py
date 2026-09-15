"""Custom Finder icons.

macOS offers no way to tell QuickLook which frame of a video to use as its poster
frame. What it does offer is a custom file icon, stored in the file's resource fork
and flagged in `com.apple.FinderInfo`, which Finder displays in place of the
generated thumbnail. Setting one is reversible: clearing it restores the default.
"""

import ctypes
import ctypes.util
from pathlib import Path

from AppKit import NSImage, NSWorkspace

FINDER_INFO_XATTR = b"com.apple.FinderInfo"
FINDER_INFO_SIZE = 32
FLAGS_OFFSET = 8  # the Finder flags word starts here; kHasCustomIcon is its 0x0400 bit
HAS_CUSTOM_ICON = 0x04  # that bit, within the high byte

_libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)


class IconError(RuntimeError):
    """Raised when a custom icon cannot be applied or removed."""


def set_icon(target: Path, image: Path) -> None:
    """Give `target` the custom Finder icon in `image`."""
    icon = NSImage.alloc().initWithContentsOfFile_(str(image))
    if icon is None or not icon.isValid():
        raise IconError(f"could not read {image.name} as an image")
    if not NSWorkspace.sharedWorkspace().setIcon_forFile_options_(icon, str(target), 0):
        raise IconError(f"macOS refused to set the icon on {target.name}")


def clear_icon(target: Path) -> None:
    """Remove any custom Finder icon from `target`, restoring the generated thumbnail."""
    # AppKit reports failure when there was no icon to remove, so the flag is the
    # authority on whether the file ended up in the state we asked for.
    cleared = NSWorkspace.sharedWorkspace().setIcon_forFile_options_(None, str(target), 0)
    if not cleared and has_custom_icon(target):
        raise IconError(f"macOS refused to clear the icon on {target.name}")


def has_custom_icon(target: Path) -> bool:
    """Report whether `target` currently carries a custom Finder icon."""
    buffer = ctypes.create_string_buffer(FINDER_INFO_SIZE)
    size = _libc.getxattr(str(target).encode(), FINDER_INFO_XATTR, buffer, FINDER_INFO_SIZE, 0, 0)
    if size < FLAGS_OFFSET + 1:
        return False
    return bool(buffer.raw[FLAGS_OFFSET] & HAS_CUSTOM_ICON)
