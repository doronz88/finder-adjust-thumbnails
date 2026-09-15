"""Frame extraction through macOS's own AVFoundation.

This is the preferred engine: no external binary, no subprocess, and it honours a
video's preferred track transform, so footage shot in portrait comes out upright
rather than on its side.

AVFoundation only understands the formats QuickTime understands — mp4, mov, m4v and
friends. Matroska, WebM and WMV are not among them, which is what `can_read` is for.
"""

import warnings
from pathlib import Path

import objc
from AppKit import NSBitmapImageRep, NSGraphicsContext, NSMakeRect, NSPNGFileType
from AVFoundation import AVAssetImageGenerator, AVURLAsset
from CoreMedia import CMTimeGetSeconds, CMTimeMakeWithSeconds
from Foundation import NSURL, NSSize

# PyObjC has no type metadata for the CGImageRef that AVAssetImageGenerator returns, so
# it hands back an untyped pointer and warns. The pointer is still accepted by the
# AppKit calls we pass it to (initWithCGImage_), which the tests here pin down.
warnings.filterwarnings("ignore", category=objc.ObjCPointerWarning)

VIDEO_MEDIA_TYPE = "vide"
TIMESCALE = 600  # CMTime ticks per second; 600 divides evenly by the usual frame rates


class UnsupportedByAVFoundation(Exception):
    """Raised internally when AVFoundation cannot handle a file."""


def _asset(video: Path) -> AVURLAsset:
    url = NSURL.fileURLWithPath_(str(video.resolve()))
    return AVURLAsset.URLAssetWithURL_options_(url, None)


def can_read(video: Path) -> bool:
    """Report whether AVFoundation can decode `video`."""
    try:
        asset = _asset(video)
    except Exception:
        return False
    return bool(asset.isReadable() and asset.tracksWithMediaType_(VIDEO_MEDIA_TYPE))


def probe_duration(video: Path) -> float:
    """Return the duration of `video` in seconds."""
    seconds = CMTimeGetSeconds(_asset(video).duration())
    if not seconds or seconds != seconds:  # NaN when the asset carries no usable duration
        raise UnsupportedByAVFoundation(f"no duration for {video.name}")
    return float(seconds)


def extract_frame(video: Path, seconds: float, destination: Path, *, size: int) -> Path:
    """Write the frame at `seconds` to `destination` as a square PNG of `size` pixels."""
    generator = AVAssetImageGenerator.assetImageGeneratorWithAsset_(_asset(video))
    generator.setAppliesPreferredTrackTransform_(True)
    generator.setMaximumSize_(NSSize(size, size))
    # Land on the requested instant rather than the nearest sync frame.
    generator.setRequestedTimeToleranceBefore_(CMTimeMakeWithSeconds(0, TIMESCALE))
    generator.setRequestedTimeToleranceAfter_(CMTimeMakeWithSeconds(0, TIMESCALE))

    at = CMTimeMakeWithSeconds(seconds, TIMESCALE)
    image = generator.copyCGImageAtTime_actualTime_error_(at, None, None)[0]
    if image is None:
        raise UnsupportedByAVFoundation(f"no frame at {seconds:.2f}s in {video.name}")

    _write_padded_png(NSBitmapImageRep.alloc().initWithCGImage_(image), destination, size)
    return destination


def _write_padded_png(frame: NSBitmapImageRep, destination: Path, size: int) -> None:
    """Centre `frame` on a transparent square canvas and write it out as a PNG.

    File icons are square and macOS stretches whatever it is given to fill that square,
    so the frame is centred at its own proportions and the rest left transparent.
    """
    width, height = frame.pixelsWide(), frame.pixelsHigh()
    scale = min(size / width, size / height)
    drawn_width, drawn_height = width * scale, height * scale

    # An RGBA canvas, so the space around the frame stays transparent.
    new_canvas = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_  # noqa: E501
    canvas = new_canvas(None, size, size, 8, 4, True, False, "NSCalibratedRGBColorSpace", 0, 0)
    context = NSGraphicsContext.graphicsContextWithBitmapImageRep_(canvas)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(context)
    try:
        frame.drawInRect_(
            NSMakeRect(
                (size - drawn_width) / 2,
                (size - drawn_height) / 2,
                drawn_width,
                drawn_height,
            )
        )
    finally:
        NSGraphicsContext.restoreGraphicsState()

    data = canvas.representationUsingType_properties_(NSPNGFileType, {})
    if data is None or not data.writeToFile_atomically_(str(destination), True):
        raise UnsupportedByAVFoundation(f"could not write {destination.name}")
