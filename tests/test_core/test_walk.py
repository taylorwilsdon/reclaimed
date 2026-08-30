"""Tests for the leaf-level directory walker, focused on virtual-filesystem
handling (``/proc/kcore`` and friends stat() at absurd sizes)."""

import os
import threading

from reclaimed.core.walk import (
    VIRTUAL_FS_ROOTS,
    WalkContext,
    WalkJob,
    _under_virtual_fs,
    list_dir,
)


def _ctx(virtual_roots):
    return WalkContext(
        skip=frozenset(),
        max_files=10,
        cancel=threading.Event(),
        virtual_roots=frozenset(virtual_roots),
    )


def test_under_virtual_fs_matches_root_and_subtree():
    roots = frozenset({os.path.join(os.sep, "proc")})
    assert _under_virtual_fs(os.path.join(os.sep, "proc"), roots)
    assert _under_virtual_fs(os.path.join(os.sep, "proc", "kcore"), roots)
    assert _under_virtual_fs(os.path.join(os.sep, "proc", "1", "maps"), roots)


def test_under_virtual_fs_rejects_lookalikes():
    roots = frozenset({os.path.join(os.sep, "proc")})
    # A sibling that merely shares a prefix, and a nested "proc" elsewhere.
    assert not _under_virtual_fs(os.path.join(os.sep, "procfs"), roots)
    assert not _under_virtual_fs(os.path.join(os.sep, "home", "u", "proc"), roots)


def test_default_roots_are_posix_only():
    if os.name == "posix":
        assert "/proc" in VIRTUAL_FS_ROOTS
        assert "/sys" in VIRTUAL_FS_ROOTS
    else:
        assert VIRTUAL_FS_ROOTS == frozenset()


def test_list_dir_skips_virtual_root_when_encountered_as_child(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "keep.bin").write_bytes(b"x" * 2000)
    fake = tmp_path / "fake"
    fake.mkdir()
    (fake / "kcore").write_bytes(b"x" * 500)

    listing = list_dir(WalkJob(0, str(tmp_path)), _ctx({str(fake)}))

    names = {name for name, _ in listing.subdirs}
    assert names == {"real"}  # "fake" is a virtual-fs root and never queued


def test_list_dir_ignores_files_inside_a_virtual_root(tmp_path):
    fake = tmp_path / "fake"
    fake.mkdir()
    (fake / "kcore").write_bytes(b"x" * 500)
    (fake / "big").write_bytes(b"x" * 9999)
    sub = fake / "1"
    sub.mkdir()
    (sub / "maps").write_bytes(b"x" * 100)

    listing = list_dir(WalkJob(0, str(fake)), _ctx({str(fake)}))

    assert listing.own_bytes == 0
    assert listing.file_count == 0
    assert listing.candidates == []
    assert listing.subdirs == []  # nested dirs are still under the virtual root


def test_list_dir_counts_normally_without_virtual_roots(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"x" * 1234)

    listing = list_dir(WalkJob(0, str(tmp_path)), _ctx(set()))

    assert listing.own_bytes == 1234
    assert listing.file_count == 1
