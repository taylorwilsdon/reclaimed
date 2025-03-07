# reclaimed ♻️
![PyPI Downloads](https://img.shields.io/pypi/dm/reclaimed?style=flat&logo=pypi&logoColor=white&label=Downloads&labelColor=005da7&color=blue)
![GitHub License](https://img.shields.io/github/license/taylorwilsdon/reddacted?style=flat&logo=github&logoColor=white&label=License&labelColor=555&color=blue)
[![Privacy Shield](https://img.shields.io/badge/Privacy-100%25_Client--Side_Processing-blue?style=flat&logo=shield&logoColor=white&labelColor=555)](https://github.com/taylorwilsdon)
![GitHub commit activity](https://img.shields.io/github/commit-activity/w/taylorwilsdon/reclaimed?style=flat&logo=github&logoColor=white&label=Commits&labelColor=24292e&color=blue)
![PyPI Version](https://img.shields.io/pypi/v/reclaimed?style=flat&logo=pypi&logoColor=white&label=Version&labelColor=005da7&color=blue)

**reclaimed** is a powerful and user-friendly command-line tool for analyzing disk usage, with special handling for iCloud storage on macOS. Quickly find your largest files and directories with a beautiful, color-coded interface, and manage them with an interactive terminal UI.

## Features

- 🚀 Fast recursive directory scanning, legitimately performant and doesn't look too choppy as it batches progress updates super efficiently
    - I basically kept timing identical runs and adjusting until I found the exact point of re-painting frequency that did not slow results by >5ms total. 
    - Separate thread for the clock so it can hum along in real time 😂
- ☁️ Smart detection & handling of iCloud Drive symlink files vs local storage which is nice on the macbook 
- 📊 Beautiful UI (uses [Textualize/rich](https://github.com/Textualize/rich) and [Textualize/textual](https://github.com/Textualize/textual) libraries)
    - Textual is dope, you can change the colors and everything - the mouse even works somehow but you can (and I do) drive this keyboard only
    - Real ones who appreciate solarized dark for the masterpiece that it is can leave it on default
- 🖥️ Interactive terminal UI for browsing and managing files/directories and a worse noninteractive mode that's not worth using unless you're purging files on a headless rpi that's barely hanging on
- 🗑️ Delete large files and directories directly from the interface (and yes, there's a safety confirmation first)
- 💾 Export results to JSON for further analysis or batch operations
- ⚡️ Real-time progress indication & graceful handling of permission issues for a smooth run every time
- 🛡️ Actual privacy - no telemetry, no analytics, no tracking - it only runs 100% offline, can't even check for updates

https://github.com/user-attachments/assets/1aae04e7-3201-414d-a1e3-6ea5d55bd691

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Technically not a venv but if you aren't using a venv you're generally doing python wrong

### Using pip (preferred)

```bash
pip install reclaimed
```

### Using Homebrew (macOS)

```bash
brew install taylorwilsdon/tap/reclaimed
```

### From Source

```bash
git clone https://github.com/taylorwilsdon/reclaimed.git
cd reclaimed
pip install -e .
```

For development:
```bash
pip install -r requirements.txt
```

## Usage

Basic usage:
```bash
reclaimed ~/Documents
```

Advanced options:
```bash
# Show more results
reclaimed ~/Documents --files 20 --dirs 15

# Save results to JSON
reclaimed ~/Documents --output results.json
```

### Options

- `PATH`: Directory to scan (default: current directory)
- `-f, --files N`: Number of largest files to show (default: 10)
- `-d, --dirs N`: Number of largest directories to show (default: 10)
- `-o, --output FILE`: Save results to JSON file
- `-i, --interactive`: Launch the interactive Textual UI

## Output

### CLI Mode
The tool provides:
- A real-time progress indicator showing files scanned and total size
- Two tables showing the largest files and directories
- Clear indication of iCloud vs local storage
- Summary of any access issues encountered

### Interactive Mode
The interactive UI provides:
- Tabbed interface to switch between files and directories views
- Keyboard navigation (arrow keys) to browse through items
- Ability to sort items by size, name, or path
- File/directory deletion with confirmation dialog
- Refresh capability to update the scan results

## Development

This project uses [UV](https://github.com/astral-sh/uv) for building and publishing, and [Hatch](https://hatch.pypa.io/) for development workflow management.

### Setup Development Environment

```bash
pip install -r requirements.txt
hatch shell
```

### Common Commands

```bash
# Run tests
hatch run test

# Run tests with coverage
hatch run test-cov

# Run linting (black, ruff, mypy)
hatch run lint

# Build distribution packages
uv build --sdist --wheel

# Publish to PyPI
uv publish

# Run with interactive UI
python -m reclaimed /path/to/scan
```

## Interactive Mode

The interactive mode launches automatically, or with the `-i` or `--interactive` flag:

```bash
reclaim ~/Documents -i
```

Non-interactive mode can be enabled (prints a simpler output with very low overhead) with `--no-interactive`

```bash
reclaim ~/Documents --no-interactive
```

### Keyboard Shortcuts

| Key       | Action                    |
|-----------|---------------------------|
| F         | Switch to Files view      |
| D         | Switch to Directories view|
| S         | Sort items                |
| R         | Refresh scan              |
| Delete    | Delete selected item      |
| ?         | Show help                 |
| Q         | Quit application          |
| Arrow keys| Navigate through items    |

### Features

- **Tabbed Interface**: Toggle between Files and Directories views
- **Sorting**: Sort items by size (default), name, or path
- **File Management**: Delete files and directories with confirmation
- **Solarized Dark Theme**: Easy on the eyes for extended use

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
