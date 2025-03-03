# reclaimed 🌟

A powerful and user-friendly command-line tool for analyzing disk usage, with special handling for iCloud storage on macOS. Quickly find your largest files and directories with a beautiful, color-coded interface, and manage them with an interactive terminal UI.

## Features

- 🚀 Fast recursive directory scanning, legitimately performant and batches progress updates efficiently 
- ☁️ Smart detection of iCloud vs local storage which is nice on the macbook
- 📊 Beautiful UI (utilizing [Textualize/rich](https://github.com/Textualize/rich) and [Textualize/textual](https://github.com/Textualize/textual) libraries)
- 🖥️ Interactive terminal UI for browsing and managing files/directories
- 🗑️ Delete large files and directories directly from the interface
- 💾 Export results to JSON for further analysis or batch operations
- ⚡️ Real-time progress indication
- 🛡️ Graceful handling of permission issues

<img width="600" alt="image" src="https://github.com/user-attachments/assets/6dc33b3e-185d-45dc-97a3-5a8b84ab27d0" />

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Technically not a venv but if you aren't using a venv you're generally doing python wrong

### Using pip (preferred)

```bash
pip install reclaimed
```

### From Source

```bash
git clone https://github.com/taylorwilsdon/reclaimed.git
cd reclaimed
pip install -r requirements.txt
hatch shell
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

This project uses [Hatch](https://hatch.pypa.io/) for development workflow management.

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
hatch build

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
