import subprocess

import pytest


@pytest.fixture(scope="session")
def sample_video(tmp_path_factory):
    """A 5 second test video whose picture changes over time."""
    path = tmp_path_factory.mktemp("videos") / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=5:size=320x240:rate=10",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
    )
    return path


@pytest.fixture(scope="session")
def sample_image(tmp_path_factory):
    """A small PNG usable as a file icon."""
    path = tmp_path_factory.mktemp("images") / "red.png"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:size=256x256",
            "-frames:v",
            "1",
            str(path),
        ],
        check=True,
    )
    return path


@pytest.fixture(scope="session")
def wide_video(tmp_path_factory):
    """A 1920x1080 video containing a 400x400 yellow square on navy.

    Anything that distorts the frame turns that square into a rectangle, which the
    tests measure directly.
    """
    path = tmp_path_factory.mktemp("wide") / "wide.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=navy:s=1920x1080:d=3",
            "-vf",
            "drawbox=x=760:y=340:w=400:h=400:color=yellow:t=fill",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
    )
    return path


def opaque_bounds(image_path, step=4):
    """Bounding box (width, height) of the non-transparent pixels of a PNG."""
    from AppKit import NSBitmapImageRep

    rep = NSBitmapImageRep.imageRepWithContentsOfFile_(str(image_path))
    assert rep is not None, f"could not read {image_path}"
    xs, ys = [], []
    for x in range(0, rep.pixelsWide(), step):
        for y in range(0, rep.pixelsHigh(), step):
            if rep.colorAtX_y_(x, y).alphaComponent() > 0.5:
                xs.append(x)
                ys.append(y)
    if not xs:
        return 0, 0
    return max(xs) - min(xs) + step, max(ys) - min(ys) + step


def colour_bounds(image_path, predicate, step=4):
    """Bounding box (width, height) of pixels satisfying `predicate(NSColor)`."""
    from AppKit import NSBitmapImageRep

    rep = NSBitmapImageRep.imageRepWithContentsOfFile_(str(image_path))
    xs, ys = [], []
    for x in range(0, rep.pixelsWide(), step):
        for y in range(0, rep.pixelsHigh(), step):
            if predicate(rep.colorAtX_y_(x, y)):
                xs.append(x)
                ys.append(y)
    if not xs:
        return 0, 0
    return max(xs) - min(xs) + step, max(ys) - min(ys) + step


def is_yellow(colour):
    return (
        colour.alphaComponent() > 0.5
        and colour.redComponent() > 0.6
        and colour.greenComponent() > 0.6
        and colour.blueComponent() < 0.4
    )


@pytest.fixture(scope="session")
def mkv_video(sample_video, tmp_path_factory):
    """A Matroska file. AVFoundation cannot read these; ffmpeg can."""
    path = tmp_path_factory.mktemp("mkv") / "sample.mkv"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(sample_video),
            "-c",
            "copy",
            str(path),
        ],
        check=True,
    )
    return path


@pytest.fixture(scope="session")
def rotated_video(tmp_path_factory):
    """A 640x360 video carrying a 90 degree display rotation, as phone footage does."""
    path = tmp_path_factory.mktemp("rotated") / "rotated.mp4"
    upright = path.with_name("upright.mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=navy:s=640x360:d=2",
            "-vf",
            "drawbox=x=120:y=80:w=200:h=200:color=yellow:t=fill",
            "-pix_fmt",
            "yuv420p",
            str(upright),
        ],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-display_rotation",
            "90",
            "-i",
            str(upright),
            "-c",
            "copy",
            str(path),
        ],
        check=True,
    )
    return path


def resource_fork_size(path) -> int:
    """Bytes the custom icon occupies in a file's resource fork."""
    listing = subprocess.run(["ls", "-l@", str(path)], capture_output=True, text=True).stdout
    line = next((line for line in listing.splitlines() if "ResourceFork" in line), None)
    return int(line.split()[-1]) if line else 0
