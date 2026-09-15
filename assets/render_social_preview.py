"""Render the GitHub social preview image.

Run with: uv run python assets/render_social_preview.py assets/social-preview.png

AppKit's origin is bottom-left, so every position below is given as a distance from the
TOP of the image and converted once, in `_rect`.
"""

import sys

from AppKit import (
    NSBezierPath,
    NSBitmapImageRep,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSGraphicsContext,
    NSMakeRect,
    NSMutableParagraphStyle,
    NSParagraphStyleAttributeName,
    NSPNGFileType,
    NSString,
)

WIDTH, HEIGHT = 1280, 640

new_canvas = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_  # noqa: E501


def rgb(red: int, green: int, blue: int, alpha: float = 1.0) -> NSColor:
    return NSColor.colorWithSRGBRed_green_blue_alpha_(red / 255, green / 255, blue / 255, alpha)


def _rect(x: float, top: float, width: float, height: float):
    """A rect placed by its distance from the top of the image."""
    return NSMakeRect(x, HEIGHT - top - height, width, height)


def regular(size: float) -> NSFont:
    return NSFont.systemFontOfSize_(size)


def bold(size: float) -> NSFont:
    return NSFont.boldSystemFontOfSize_(size)


def mono(size: float) -> NSFont:
    return NSFont.monospacedSystemFontOfSize_weight_(size, 0.0)


def text(body, x, top, size, colour, font=regular, width=None) -> None:
    attributes = {
        NSFontAttributeName: font(size),
        NSForegroundColorAttributeName: colour,
        NSParagraphStyleAttributeName: NSMutableParagraphStyle.alloc().init(),
    }
    NSString.stringWithString_(body).drawInRect_withAttributes_(
        _rect(x, top, width or (WIDTH - x - 40), size * 1.6), attributes
    )


def draw() -> None:
    rgb(21, 23, 28).set()
    NSBezierPath.fillRect_(NSMakeRect(0, 0, WIDTH, HEIGHT))

    # A soft accent bar down the left edge.
    rgb(96, 165, 250).set()
    NSBezierPath.fillRect_(NSMakeRect(0, 0, 6, HEIGHT))

    text("finder-adjust-thumbnails", 72, 150, 50, rgb(242, 245, 250), bold, width=700)
    text(
        "Pick the frame Finder shows for your videos.",
        74,
        224,
        26,
        rgb(154, 163, 178),
        width=700,
    )

    rgb(31, 34, 41).set()
    NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(_rect(72, 300, 640, 54), 8, 8).fill()
    text(
        "finder-adjust-thumbnails ~/Movies --offset 25%",
        92,
        316,
        19,
        rgb(134, 209, 156),
        mono,
        width=620,
    )

    text(
        "AVFoundation first  ·  ffmpeg only as a fallback  ·  --clear to undo",
        74,
        402,
        18,
        rgb(116, 124, 139),
        width=700,
    )

    rgb(70, 77, 92).set()
    NSBezierPath.fillRect_(_rect(74, 492, 96, 1))
    text(
        "github.com/doronz88/finder-adjust-thumbnails",
        74,
        512,
        17,
        rgb(96, 104, 120),
        width=700,
    )

    # The point of the whole tool: a wide frame, undistorted, inside a square icon.
    slot_x, slot_top, slot = 852, 168, 288

    text(
        "the square icon macOS insists on",
        slot_x,
        slot_top - 34,
        16,
        rgb(108, 116, 130),
        width=slot + 40,
    )

    rgb(74, 81, 96).set()
    border = NSBezierPath.bezierPathWithRect_(_rect(slot_x, slot_top, slot, slot))
    border.setLineWidth_(2.0)
    border.setLineDash_count_phase_([7.0, 6.0], 2, 0.0)
    border.stroke()

    frame_height = slot * 9 / 16
    frame_top = slot_top + (slot - frame_height) / 2
    rgb(37, 99, 183).set()
    NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
        _rect(slot_x, frame_top, slot, frame_height), 6, 6
    ).fill()

    rgb(236, 241, 249, 0.96).set()
    play = NSBezierPath.bezierPath()
    centre_x = slot_x + slot / 2
    centre_y = HEIGHT - (frame_top + frame_height / 2)
    radius = 26
    play.moveToPoint_((centre_x - radius * 0.45, centre_y + radius * 0.6))
    play.lineToPoint_((centre_x - radius * 0.45, centre_y - radius * 0.6))
    play.lineToPoint_((centre_x + radius * 0.7, centre_y))
    play.closePath()
    play.fill()

    text(
        "your frame, at its real proportions",
        slot_x,
        slot_top + slot + 18,
        16,
        rgb(108, 116, 130),
        width=slot + 40,
    )


def main() -> None:
    destination = sys.argv[1] if len(sys.argv) > 1 else "assets/social-preview.png"
    canvas = new_canvas(None, WIDTH, HEIGHT, 8, 4, True, False, "NSCalibratedRGBColorSpace", 0, 0)
    context = NSGraphicsContext.graphicsContextWithBitmapImageRep_(canvas)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(context)
    try:
        draw()
    finally:
        NSGraphicsContext.restoreGraphicsState()
    canvas.representationUsingType_properties_(NSPNGFileType, {}).writeToFile_atomically_(
        destination, True
    )
    print(f"wrote {destination}")


if __name__ == "__main__":
    main()
