"""Utilities for formatting data."""

from typing import List, Tuple


class SizeFormatter:
    """Format file sizes in human-readable format."""

    # Size units from bytes to petabytes
    UNITS: List[Tuple[float, str]] = [
        (1, "B"),
        (1024, "KB"),
        (1024 * 1024, "MB"),
        (1024 * 1024 * 1024, "GB"),
        (1024 * 1024 * 1024 * 1024, "TB"),
        (1024 * 1024 * 1024 * 1024 * 1024, "PB"),
    ]

    @classmethod
    def format_size(cls, size: int, precision: int = 1) -> str:
        """Convert a size in bytes to a human-readable string.

        Args:
            size: Size in bytes
            precision: Number of decimal places to show

        Returns:
            Human-readable size string (e.g., "1.5 GB")
        """
        if size < 0:
            raise ValueError("Size cannot be negative")

        # Handle zero size
        if size == 0:
            return f"0.0 {cls.UNITS[0][1]}"

        # Find appropriate unit
        for threshold, unit in reversed(cls.UNITS):
            if size >= threshold:
                value = size / threshold
                return f"{value:.{precision}f} {unit}"

        # Should never reach here
        return f"{size} B"

    @classmethod
    def parse_size(cls, size_str: str) -> int:
        """Convert a human-readable size string back to bytes.

        Args:
            size_str: Size string (e.g., "1.5 GB")

        Returns:
            Size in bytes

        Raises:
            ValueError: If size string is invalid
        """
        size_str = size_str.strip().upper()
        if not size_str:
            raise ValueError("Empty size string")

        # Split into value and unit
        try:
            parts = size_str.split()
            if len(parts) != 2:
                raise ValueError
            value = float(parts[0])
            unit = parts[1]
        except ValueError:
            raise ValueError(f"Invalid size format: {size_str}") from None

        # Find unit multiplier
        for threshold, unit_name in cls.UNITS:
            if unit == unit_name:
                return int(value * threshold)

        raise ValueError(f"Unknown unit: {unit}")


def format_size(size: int, precision: int = 1) -> str:
    """Convenience function for formatting sizes.

    Args:
        size: Size in bytes
        precision: Number of decimal places

    Returns:
        Human-readable size string
    """
    return SizeFormatter.format_size(size, precision)


def parse_size(size_str: str) -> int:
    """Convenience function for parsing size strings.

    Args:
        size_str: Size string to parse

    Returns:
        Size in bytes
    """
    return SizeFormatter.parse_size(size_str)
