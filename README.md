<p align="center">
  <img src="https://raw.githubusercontent.com/taylorwilsdon/reclaimed/main/reclaimed-social-transparent.png" alt="Reclaimed — disk space management" width="100%">
</p>

<p align="center">
  Fast, local disk-usage analysis with a responsive terminal interface.
</p>

<p align="center">
  <a href="https://pypi.org/project/reclaimed/"><img src="https://img.shields.io/pypi/v/reclaimed?style=flat-square&label=PyPI" alt="PyPI version"></a>
  <a href="https://pypi.org/project/reclaimed/"><img src="https://img.shields.io/pypi/pyversions/reclaimed?style=flat-square" alt="Supported Python versions"></a>
  <a href="https://pepy.tech/project/reclaimed"><img src="https://static.pepy.tech/badge/reclaimed" alt="PyPI downloads"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/github/license/taylorwilsdon/reclaimed?style=flat-square" alt="MIT license"></a>
</p>

Reclaimed recursively scans a directory, calculates its largest files and directory trees, and presents the results in either an interactive [Textual](https://textual.textualize.io/) application or compact [Rich](https://rich.readthedocs.io/) tables. It runs entirely on your machine, makes no network requests, and includes no telemetry.

| Scanner | Interactive UI | Output |
|:--|:--|:--|
| Bounded top-file tracking, exact recursive directory totals, 1–8 directory-listing workers | Responsive side-by-side or stacked tables, live scan metrics, keyboard and mouse control | Proportional size bars, access-issue reporting, local JSON export |
| Ignores symlinks and skips common trash/system directories by default | Sort, hide, rescan, switch themes, or permanently delete with confirmation | Partial results are retained when a text-mode scan is interrupted |

Reclaimed supports Python 3.9+ on macOS, Linux, and Windows.

## Install

| Run without installing | Install with pip | Install with Homebrew on macOS |
|:--|:--|:--|
| `uvx reclaimed` | `python -m pip install reclaimed` | `brew install taylorwilsdon/tap/reclaimed` |

To work from a clone instead:

```bash
git clone https://github.com/taylorwilsdon/reclaimed.git
cd reclaimed
python -m pip install -e .
```

## Use

Interactive mode is the default. Pass a directory, or omit `PATH` to scan the current directory.

```bash
# Open the interactive interface
reclaimed ~/Documents

# Print Rich tables and exit
reclaimed ~/Documents --no-interactive

# Keep more results and use all eight workers
reclaimed ~/Documents --files 25 --dirs 20 --jobs 8

# Add directory names to the default skip list
reclaimed ~/Documents -s node_modules -s __pycache__

# Export the retained results and scan metadata
reclaimed ~/Documents --output results.json
```

When `--output` is used with the interactive interface, the JSON file is written after the app exits. In text mode, pressing <kbd>Ctrl</kbd>+<kbd>C</kbd> prints and optionally exports the partial results collected so far.

### Command-line reference

| Argument or option | Purpose |
|:--|:--|
| `PATH` | Directory to scan; defaults to the current directory |
| `-f, --max-files, --files N` | Keep the `N` largest files; default `10`, minimum `0` |
| `-d, --max-dirs, --dirs N` | Keep the `N` largest directories; default `10`, minimum `0` |
| `-j, --jobs N` | Directory-listing workers; default `4`, range `1–8` |
| `-s, --skip-dirs NAME` | Skip an additional directory name; repeat for multiple names |
| `-i, --interactive / --no-interactive` | Select the Textual interface or one-shot Rich output |
| `-o, --output FILE` | Write scan metadata, retained results, and access issues to JSON |
| `--debug` | Enable debug logging |
| `--version` | Print the installed version and exit |

`.Trash` and `System Volume Information` are always included in the skip list. Additional `--skip-dirs` values are matched by directory name.

## Interactive interface

The interface updates while the scan runs and adapts to the terminal width: result panels sit side by side in wide terminals and stack in compact terminals. Each result shows its size, share of the scanned total, and path; a storage column appears when a scan is configured to identify iCloud content.

The summary strip tracks discovered size, file count, elapsed time, and hidden items. Hiding a directory only removes it and its descendants from the current view. Deletion removes the selected item from disk and always requires confirmation.

| Key | Action | Key | Action |
|:--:|:--|:--:|:--|
| <kbd>F</kbd> | Focus files | <kbd>D</kbd> | Focus directories |
| <kbd>Tab</kbd> | Switch result table | <kbd>S</kbd> | Open sort control |
| <kbd>H</kbd> | Hide selected directory | <kbd>U</kbd> | Restore hidden directories |
| <kbd>Delete</kbd> | Delete selected item | <kbd>R</kbd> | Rescan |
| <kbd>T</kbd> | Cycle theme | <kbd>Ctrl</kbd>+<kbd>P</kbd> | Open command palette |
| <kbd>?</kbd> | Show help | <kbd>Q</kbd> | Quit |

Results can be sorted by size, modification time, name, or path. The built-in theme cycle includes Solarized Dark, Nord, Rose Pine Moon, Catppuccin Mocha, Atom One Dark, and Textual Light.

## Text output and JSON

Text mode prints the same largest-file and largest-directory sets without starting the full-screen interface. Tables use relative, end-preserving paths, proportional bars, percentages, and an iCloud/local storage column only when relevant. Permission and other access failures are summarized after the results instead of aborting the scan.

JSON exports contain:

- Scan timestamp, root path, total bytes, formatted total, and number of files scanned
- Largest files and directories with absolute paths, byte and formatted sizes, and storage type
- Paths that could not be read and their error messages

## Python API

The scanner can also be embedded. On macOS, set `icloud_base` to classify results inside the iCloud Drive tree:

```python
from pathlib import Path

from reclaimed import DiskScanner, ScanOptions

options = ScanOptions(
    max_files=25,
    max_dirs=20,
    max_workers=4,
    icloud_base=Path.home() / "Library" / "Mobile Documents",
)
result = DiskScanner(options).scan(Path.home())
```

`scan_async()` yields progress snapshots while directory listings run off the event loop. An interrupted synchronous scan raises `ScanInterruptedError` with the collected `ScanResult` available as `error.partial`.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the development workflow and [pyproject.toml](./pyproject.toml) for supported Python versions, dependencies, and tool configuration.

## License

Reclaimed is available under the [MIT License](./LICENSE).
