"""Utility for trimming trailing whitespace from files."""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional


def get_git_tracked_python_files(root_dir: Path) -> List[Path]:
    """Find all Python files tracked by git in the repository."""
    try:
        # Run git ls-files to get all tracked files
        result = subprocess.run(
            ["git", "-C", str(root_dir), "ls-files", "*.py"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Convert the output to a list of Path objects
        return [root_dir / file for file in result.stdout.splitlines() if file.strip()]
    except subprocess.SubprocessError:
        # Fallback if git command fails
        print("Warning: Could not get git tracked files. Falling back to manual search.")
        return _fallback_get_python_files(root_dir)


def _fallback_get_python_files(root_dir: Path) -> List[Path]:
    """Fallback method to find Python files if git command fails."""
    python_files = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)
    return python_files


def trim_trailing_whitespace(file_path: Path) -> bool:
    """
    Remove trailing whitespace from a file.

    Returns True if changes were made, False otherwise.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Check if there are any lines with trailing whitespace
    has_trailing_whitespace = any(re.search(r"[ \t]+$", line) for line in lines)
    if not has_trailing_whitespace:
        return False

    # Remove trailing whitespace
    trimmed_lines = [re.sub(r"[ \t]+$", "", line) for line in lines]

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(trimmed_lines)

    return True


def trim_all_files(root_dir: Optional[Path] = None, verbose: bool = False) -> int:
    """
    Trim trailing whitespace from all git-tracked Python files in the repository.

    Returns the number of files modified.
    """
    if root_dir is None:
        # Find the repository root (assuming this file is in the repo)
        current_file = Path(__file__)
        root_dir = current_file
        while not (root_dir / ".git").exists():
            root_dir = root_dir.parent
            if root_dir == root_dir.parent:  # Reached filesystem root
                root_dir = current_file.parent.parent
                break

    python_files = get_git_tracked_python_files(root_dir)
    modified_count = 0

    for file_path in python_files:
        if trim_trailing_whitespace(file_path):
            modified_count += 1
            if verbose:
                print(f"Trimmed whitespace in {file_path.relative_to(root_dir)}")

    if verbose:
        print(f"Modified {modified_count} file(s)")

    return modified_count


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Trim trailing whitespace from git-tracked Python files"
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Root directory to search for files (default: repository root)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Print information about modified files"
    )
    parser.add_argument(
        "--staged-only", action="store_true", help="Only process files staged for commit"
    )

    args = parser.parse_args()

    if args.staged_only and args.path is None:
        # Get only staged Python files
        try:
            root_dir = Path(__file__)
            while not (root_dir / ".git").exists():
                root_dir = root_dir.parent
                if root_dir == root_dir.parent:
                    root_dir = None
                    break

            if root_dir:
                result = subprocess.run(
                    [
                        "git",
                        "-C",
                        str(root_dir),
                        "diff",
                        "--cached",
                        "--name-only",
                        "--diff-filter=ACMR",
                        "*.py",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                files = [root_dir / f for f in result.stdout.splitlines() if f.strip()]

                modified_count = 0
                for file_path in files:
                    if trim_trailing_whitespace(file_path):
                        modified_count += 1
                        if args.verbose:
                            print(f"Trimmed whitespace in {file_path.relative_to(root_dir)}")

                if args.verbose:
                    print(f"Modified {modified_count} staged file(s)")
            else:
                print("Error: Could not find git repository root")
        except subprocess.SubprocessError as e:
            print(f"Error getting staged files: {e}")
    else:
        trim_all_files(args.path, args.verbose)
