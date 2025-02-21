#!/usr/bin/env python3
"""
Disk Space Scanner - Analyze directory sizes and find large files
"""
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple
import os
import sys
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
        self._scanned_paths: Dict[Path, int] = {}
        self._icloud_base = Path.home() / "Library/Mobile Documents"
        
    def scan_directory(self, root_path: Path) -> Tuple[List[FileInfo], List[FileInfo]]:
        """
        Scan directory and return largest files and folders
        
        Args:
            root_path: Directory path to scan
            
        Returns:
            Tuple of (largest_files, largest_dirs)
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            task = progress.add_task("Scanning...", total=None)
            
            try:
                for path in self._walk_directory(root_path, progress):
                    if path.is_file():
                        try:
                            size = path.stat().st_size
                            is_icloud = self._icloud_base in path.parents
                            self._scanned_paths[path] = (size, is_icloud)
                        except (PermissionError, OSError) as e:
                            self.console.print(f"[yellow]Warning: Cannot access {path}: {e}")
                    progress.update(task)
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Scan interrupted. Showing partial results...")
        
        # Get largest files and directories
        files = [FileInfo(p, s, i) for p, (s, i) in self._scanned_paths.items() if p.is_file()]
        files.sort(key=lambda x: x.size, reverse=True)
        
        dirs = self._calculate_dir_sizes(root_path)
        
        return files[:10], dirs[:10]
    
    def _walk_directory(self, path: Path, progress: Progress):
        """Recursively walk directory handling permissions"""
        try:
            for item in path.iterdir():
                if item.is_dir() and not item.is_symlink():
                    yield from self._walk_directory(item, progress)
                yield item
        except PermissionError as e:
            self.console.print(f"[yellow]Warning: Cannot access {path}: {e}")
    
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
