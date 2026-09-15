import shutil

import pytest

from finder_adjust_thumbnails.adjust import Status, apply_offset, clear_thumbnail, run_batch
from finder_adjust_thumbnails.icons import has_custom_icon
from finder_adjust_thumbnails.offsets import parse_offset


@pytest.fixture
def video(sample_video, tmp_path):
    copy = tmp_path / "clip.mp4"
    shutil.copy(sample_video, copy)
    return copy


def test_applying_an_offset_gives_the_file_a_custom_icon(video):
    result = apply_offset(video, parse_offset("2"), dry_run=False)

    assert result.status is Status.UPDATED
    assert has_custom_icon(video)


def test_result_reports_the_resolved_second(video):
    result = apply_offset(video, parse_offset("50%"), dry_run=False)

    assert "2.5" in result.detail


def test_dry_run_changes_nothing_on_disk(video):
    result = apply_offset(video, parse_offset("2"), dry_run=True)

    assert result.status is Status.WOULD_UPDATE
    assert not has_custom_icon(video)


def test_a_file_that_is_not_really_a_video_fails_without_raising(tmp_path):
    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"not a video")

    result = apply_offset(broken, parse_offset("2"), dry_run=False)

    assert result.status is Status.FAILED
    assert result.detail


def test_clearing_removes_the_custom_icon(video):
    apply_offset(video, parse_offset("2"), dry_run=False)

    result = clear_thumbnail(video, dry_run=False)

    assert result.status is Status.CLEARED
    assert not has_custom_icon(video)


def test_clearing_a_file_without_a_custom_icon_is_skipped(video):
    result = clear_thumbnail(video, dry_run=False)

    assert result.status is Status.SKIPPED


def test_dry_run_clear_leaves_the_icon_in_place(video):
    apply_offset(video, parse_offset("2"), dry_run=False)

    result = clear_thumbnail(video, dry_run=True)

    assert result.status is Status.WOULD_CLEAR
    assert has_custom_icon(video)


def test_run_batch_processes_every_file_and_keeps_going_after_a_failure(video, tmp_path):
    second = tmp_path / "second.mp4"
    shutil.copy(video, second)
    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"not a video")

    results = run_batch([video, broken, second], offset=parse_offset("1"), dry_run=False, jobs=2)

    by_status = {result.path.name: result.status for result in results}
    assert by_status == {
        "clip.mp4": Status.UPDATED,
        "second.mp4": Status.UPDATED,
        "broken.mp4": Status.FAILED,
    }
    assert has_custom_icon(video) and has_custom_icon(second)


def test_run_batch_returns_results_in_input_order(video, tmp_path):
    others = []
    for name in ("b.mp4", "a.mp4", "c.mp4"):
        copy = tmp_path / name
        shutil.copy(video, copy)
        others.append(copy)

    results = run_batch(others, offset=parse_offset("1"), dry_run=True, jobs=3)

    assert [result.path.name for result in results] == ["b.mp4", "a.mp4", "c.mp4"]


def test_icon_writes_never_happen_on_a_worker_thread(video, tmp_path, monkeypatch):
    """AppKit's icon API is not thread safe: concurrent calls deadlock in IconServices."""
    import threading

    from finder_adjust_thumbnails import adjust as adjust_module

    threads = []
    real_set_icon = adjust_module.set_icon

    def recording_set_icon(target, image):
        threads.append(threading.current_thread())
        real_set_icon(target, image)

    monkeypatch.setattr(adjust_module, "set_icon", recording_set_icon)

    copies = []
    for name in ("a.mp4", "b.mp4", "c.mp4", "d.mp4"):
        copy = tmp_path / name
        shutil.copy(video, copy)
        copies.append(copy)

    run_batch(copies, offset=parse_offset("1"), dry_run=False, jobs=4)

    assert threads, "set_icon was never called"
    assert all(thread is threading.main_thread() for thread in threads)


def test_a_batch_of_many_files_completes(video, tmp_path):
    copies = []
    for index in range(12):
        copy = tmp_path / f"many{index}.mp4"
        shutil.copy(video, copy)
        copies.append(copy)

    results = run_batch(copies, offset=parse_offset("1"), dry_run=False, jobs=8)

    assert all(result.status is Status.UPDATED for result in results)
    assert all(has_custom_icon(copy) for copy in copies)


def test_a_smaller_icon_size_stores_less_data(video, tmp_path):
    """Icon size is what the user pays for on disk, in every file's resource fork."""
    from conftest import resource_fork_size

    roomy = tmp_path / "roomy.mp4"
    shutil.copy(video, roomy)

    run_batch([video], offset=parse_offset("1"), dry_run=False, jobs=1, icon_size=256)
    run_batch([roomy], offset=parse_offset("1"), dry_run=False, jobs=1, icon_size=1024)

    assert 0 < resource_fork_size(video) < resource_fork_size(roomy)
