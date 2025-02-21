#!/usr/bin/env python3
"""
Disk Space Scanner - Analyze directory sizes and find large files
"""
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple
import os
import sys
import json
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

class FileInfo(NamedTuple):
    """Store file information in an immutable structure"""
    path: Path
    size: int
    is_icloud: bool = False

class DiskScanner:
    """Core scanning logic for analyzing disk usage"""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self._scanned_paths: Dict[Path, tuple[int, bool]] = {}
        self._icloud_base = Path.home() / "Library/Mobile Documents"
        self._access_issues: Dict[Path, str] = {}
        self._total_size = 0
        self._file_count = 0
        
    def scan_directory(
        self, 
        root_path: Path, 
        max_files: int = 10, 
        max_dirs: int = 10
    ) -> Tuple[List[FileInfo], List[FileInfo]]:
        """
        Scan directory and return largest files and folders
        
        Args:
            root_path: Directory path to scan
            max_files: Maximum number of files to return
            max_dirs: Maximum number of directories to return
            
        Returns:
            Tuple of (largest_files, largest_dirs)
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TextColumn("[cyan]{task.fields[files]} files"),
            TextColumn("[magenta]{task.fields[size]}"),
            console=self.console,
            transient=True,
        ) as progress:
            task = progress.add_task("Scanning...", total=None, files="0", size="0 B")
            
            try:
                for path in self._walk_directory(root_path, progress):
                    if path.is_file():
                        try:
                            size = path.stat().st_size
                            is_icloud = self._icloud_base in path.parents
                            self._scanned_paths[path] = (size, is_icloud)
                            self._total_size += size
                            self._file_count += 1
                            progress.update(task, files=f"{self._file_count:,}", size=self.format_size(self._total_size))
                        except (PermissionError, OSError) as e:
                            self._access_issues[path] = str(e)
                    progress.update(task)
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Scan interrupted. Showing partial results...")
        
        # Get largest files and directories
        files = [FileInfo(p, s, i) for p, (s, i) in self._scanned_paths.items() if p.is_file()]
        files.sort(key=lambda x: x.size, reverse=True)
        
        dirs = self._calculate_dir_sizes(root_path)
        
        # Show organized summary of access issues if any occurred
        if self._access_issues:
            # Group issues by error type
            issues_by_type: Dict[str, List[Path]] = {}
            for path, error in self._access_issues.items():
                issues_by_type.setdefault(error, []).append(path)
            
            issue_table = Table(
                show_header=False,
                box=None,
                padding=(0, 1),
                expand=True,
                title="[bold yellow]Access Issues Summary[/]",
                title_justify="left",
                border_style="yellow"
            )
            
            for error_type, paths in issues_by_type.items():
                issue_table.add_row(
                    "[yellow]•[/yellow]",
                    f"[yellow]{error_type}[/yellow] ({len(paths)} items)"
                )
                # Show up to 3 examples for each error type
                for path in sorted(paths)[:3]:
                    issue_table.add_row(
                        "  [dim]>[/dim]",
                        f"[dim]{path.name}[/dim]"
                    )
                if len(paths) > 3:
                    issue_table.add_row(
                        "  [dim]>[/dim]",
                        f"[dim]...and {len(paths) - 3} more similar items[/dim]"
                    )
            
            self.console.print(issue_table)
            self.console.print()

        return files[:max_files], dirs[:max_dirs]
    
    def _walk_directory(self, path: Path, progress: Progress):
        """Recursively walk directory handling permissions"""
        try:
            for item in path.iterdir():
                if item.is_dir() and not item.is_symlink():
                    # Skip certain system directories that commonly cause permission issues
                    if any(skip in str(item) for skip in ['.Trash', 'System Volume Information']):
                        continue
                    yield from self._walk_directory(item, progress)
                yield item
        except PermissionError as e:
            self._access_issues[path] = "Permission denied"
        except OSError as e:
            self._access_issues[path] = str(e)
    
    def _calculate_dir_sizes(self, root: Path) -> List[FileInfo]:
        """Calculate directory sizes from scanned files"""
        dir_sizes: Dict[Path, tuple[int, bool]] = {}
        
        for path, (size, is_icloud) in self._scanned_paths.items():
            for parent in path.parents:
                if parent < root:
                    break
                curr_size, curr_cloud = dir_sizes.get(parent, (0, is_icloud))
                dir_sizes[parent] = (curr_size + size, curr_cloud or is_icloud)
        
        dirs = [FileInfo(p, s, c) for p, (s, c) in dir_sizes.items()]
        dirs.sort(key=lambda x: x.size, reverse=True)
        return dirs

    def format_size(self, size: int) -> str:
        """Convert size in bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def save_results(self, output_path: Path, files: List[FileInfo], dirs: List[FileInfo], scanned_path: Path) -> None:
        """Save scan results to JSON file"""
        results = {
            "scan_info": {
                "timestamp": datetime.now().isoformat(),
                "scanned_path": str(scanned_path.absolute()),
                "total_size_bytes": self._total_size,
                "total_size_human": self.format_size(self._total_size),
                "files_scanned": self._file_count
            },
            "largest_files": [
                {
                    "path": str(f.path.absolute()),
                    "size_bytes": f.size,
                    "size_human": self.format_size(f.size),
                    "storage_type": "icloud" if f.is_icloud else "local"
                }
                for f in files
            ],
            "largest_directories": [
                {
                    "path": str(d.path.absolute()),
                    "size_bytes": d.size,
                    "size_human": self.format_size(d.size),
                    "storage_type": "icloud" if d.is_icloud else "local"
                }
                for d in dirs
            ],
            "access_issues": [
                {
                    "path": str(path),
                    "error": error
                }
                for path, error in self._access_issues.items()
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
