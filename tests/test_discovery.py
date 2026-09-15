from finder_adjust_thumbnails.discovery import (
    DEFAULT_EXTENSIONS,
    collect_videos,
    find_videos,
    parse_extensions,
)


def make_files(root, *names):
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()


def test_finds_videos_by_extension_and_ignores_other_files(tmp_path):
    make_files(tmp_path, "a.mp4", "b.mov", "notes.txt", "cover.jpg")

    found = find_videos(tmp_path, DEFAULT_EXTENSIONS, recursive=False)

    assert [p.name for p in found] == ["a.mp4", "b.mov"]


def test_extension_matching_is_case_insensitive(tmp_path):
    make_files(tmp_path, "LOUD.MP4")

    assert [p.name for p in find_videos(tmp_path, DEFAULT_EXTENSIONS, recursive=False)] == [
        "LOUD.MP4"
    ]


def test_non_recursive_search_skips_subdirectories(tmp_path):
    make_files(tmp_path, "top.mp4", "sub/deep.mp4")

    assert [p.name for p in find_videos(tmp_path, DEFAULT_EXTENSIONS, recursive=False)] == [
        "top.mp4"
    ]


def test_recursive_search_includes_subdirectories(tmp_path):
    make_files(tmp_path, "top.mp4", "sub/deep.mp4")

    found = find_videos(tmp_path, DEFAULT_EXTENSIONS, recursive=True)

    assert [p.name for p in found] == ["top.mp4", "deep.mp4"]


def test_hidden_files_are_skipped(tmp_path):
    make_files(tmp_path, "visible.mp4", "._resource.mp4", ".hidden.mp4")

    assert [p.name for p in find_videos(tmp_path, DEFAULT_EXTENSIONS, recursive=False)] == [
        "visible.mp4"
    ]


def test_results_are_sorted_for_stable_output(tmp_path):
    make_files(tmp_path, "c.mp4", "a.mp4", "b.mp4")

    assert [p.name for p in find_videos(tmp_path, DEFAULT_EXTENSIONS, recursive=False)] == [
        "a.mp4",
        "b.mp4",
        "c.mp4",
    ]


def test_custom_extension_list_limits_the_search(tmp_path):
    make_files(tmp_path, "a.mp4", "b.mkv")

    assert [p.name for p in find_videos(tmp_path, {"mkv"}, recursive=False)] == ["b.mkv"]


def test_parse_extensions_normalises_separators_dots_and_case():
    assert parse_extensions("MP4, .mkv,mov") == {"mp4", "mkv", "mov"}


def test_collect_videos_accepts_a_single_file(tmp_path):
    make_files(tmp_path, "a.mp4", "b.mp4")

    found = collect_videos(tmp_path / "a.mp4", DEFAULT_EXTENSIONS, recursive=False)

    assert [p.name for p in found] == ["a.mp4"]


def test_an_explicitly_named_file_is_used_whatever_its_extension(tmp_path):
    make_files(tmp_path, "clip.weird")

    found = collect_videos(tmp_path / "clip.weird", DEFAULT_EXTENSIONS, recursive=False)

    assert [p.name for p in found] == ["clip.weird"]


def test_collect_videos_on_a_directory_searches_it(tmp_path):
    make_files(tmp_path, "a.mp4", "notes.txt")

    found = collect_videos(tmp_path, DEFAULT_EXTENSIONS, recursive=False)

    assert [p.name for p in found] == ["a.mp4"]


def test_wmv_is_recognised_by_default(tmp_path):
    make_files(tmp_path, "movie.wmv")

    assert [p.name for p in find_videos(tmp_path, DEFAULT_EXTENSIONS, recursive=False)] == [
        "movie.wmv"
    ]
