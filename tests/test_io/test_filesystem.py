"""Tests for filesystem error mapping.

The scanner's error types intentionally share names with builtin exceptions.
Importing them unqualified shadows the builtins that ``os.stat`` and
``os.scandir`` actually raise, which silently makes the specific ``except``
clauses unreachable and degrades every failure into a generic ``IOError``.
These tests pin the mapping so that regression cannot return unnoticed.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from reclaimed.core import errors
from reclaimed.io import FileSystemOperations


def test_missing_file_raises_file_not_found(temp_dir: Path) -> None:
    missing = temp_dir / "no_such_file.txt"

    with pytest.raises(errors.FileNotFoundError) as excinfo:
        FileSystemOperations.get_file_size(missing)

    assert "File not found" in str(excinfo.value)
    assert isinstance(excinfo.value.original_error, FileNotFoundError)


def test_missing_file_is_not_reported_as_generic_io_error(temp_dir: Path) -> None:
    with pytest.raises(errors.AccessError) as excinfo:
        FileSystemOperations.get_file_size(temp_dir / "absent.bin")

    assert not isinstance(excinfo.value, errors.IOError)


def test_get_file_size_returns_size(temp_dir: Path) -> None:
    target = temp_dir / "sized.txt"
    target.write_text("x" * 321)

    assert FileSystemOperations.get_file_size(target) == 321


def test_scandir_on_non_directory_raises_invalid_path(temp_dir: Path) -> None:
    target = temp_dir / "plain.txt"
    target.write_text("data")

    # Validation is eager: callers should not need to advance the returned
    # iterator before discovering that the input is invalid.
    with pytest.raises(errors.InvalidPathError):
        FileSystemOperations.safe_scandir(target)


def test_scandir_yields_entries(sample_file_structure: Path) -> None:
    names = {entry.name for entry in FileSystemOperations.safe_scandir(sample_file_structure)}

    assert {"dir1", "dir2"} <= names


def test_permission_denied_maps_to_permission_error(temp_dir: Path) -> None:
    locked = temp_dir / "locked"
    locked.mkdir()
    (locked / "inside.txt").write_text("hidden")
    locked.chmod(0o000)

    try:
        if FileSystemOperations.is_directory_accessible(locked):
            pytest.skip("directory remained readable (test likely running as root)")

        with pytest.raises(errors.PermissionError) as excinfo:
            list(FileSystemOperations.safe_scandir(locked))

        assert "Permission denied" in str(excinfo.value)
    finally:
        locked.chmod(0o700)


def test_symlink_result_is_not_stale_when_path_is_replaced(temp_dir: Path) -> None:
    target = temp_dir / "target"
    target.write_text("data")
    entry = temp_dir / "entry"
    entry.write_text("ordinary file")

    assert not FileSystemOperations.is_symlink(entry)

    entry.unlink()
    entry.symlink_to(target)

    assert FileSystemOperations.is_symlink(entry)


def test_case_sensitivity_probe_retries_cleanup_after_unlink_error(temp_dir: Path) -> None:
    real_unlink = os.unlink
    attempts = 0

    def fail_first_unlink(path: str) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("transient cleanup failure")
        real_unlink(path)

    with patch("reclaimed.io.filesystem.os.unlink", side_effect=fail_first_unlink):
        FileSystemOperations.is_path_case_sensitive(temp_dir)

    assert attempts == 2
    assert not list(temp_dir.glob(".ReClAiMeD_CaSe_PrObE_*"))
