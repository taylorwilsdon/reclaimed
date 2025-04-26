# reclaimed ♻️

<p align="center">
  <img src="https://img.shields.io/pypi/dm/reclaimed?style=flat&logo=pypi&logoColor=white&label=Downloads&labelColor=005da7&color=blue" alt="PyPI Downloads" />
  <img src="https://img.shields.io/github/license/taylorwilsdon/reddacted?style=flat&logo=github&logoColor=white&label=License&labelColor=555&color=blue" alt="License" />
  <a href="https://github.com/taylorwilsdon">
    <img src="https://img.shields.io/badge/Privacy-100%25_Client--Side_Processing-blue?style=flat&logo=shield&logoColor=white&labelColor=555" alt="Privacy Shield" />
  </a>
  <img src="https://img.shields.io/github/commit-activity/w/taylorwilsdon/reclaimed?style=flat&logo=github&logoColor=white&label=Commits&labelColor=24292e&color=blue" alt="Commit Activity" />
  <img src="https://img.shields.io/pypi/v/reclaimed?style=flat&logo=pypi&logoColor=white&label=Version&labelColor=005da7&color=blue" alt="PyPI Version" />
</p>

---

**reclaimed** is a cross-platform, ultra-lightweight, and surprisingly powerful command-line tool for analyzing disk usage — with special handling for iCloud storage on macOS.  
Quickly find your largest files and directories with a beautiful, color-coded interface, and manage them through an interactive terminal UI.  
Fully supports **Linux**, **macOS**, and **Windows**.

---

## ✨ Features

- 🚀 **Legitimately Performant**: Fast recursive directory scanning with ultra-efficient progress updates.
  - Carefully tuned repaint frequency — optimized to avoid slowing results by even 5ms.
  - Separate thread for the clock to keep real-time updates buttery smooth.
- ☁️ **iCloud Smartness**: Detects and handles iCloud Drive symlink files vs local storage (macOS).
- 📊 **Beautiful UI**: Powered by [Textualize/rich](https://github.com/Textualize/rich) and [Textualize/textual](https://github.com/Textualize/textual).
  - Full keyboard navigation, mouse support, and customizable themes.
- 🖥️ **Interactive Terminal UI**: Browse, manage, and delete files/directories with ease.
- 🗑️ **Safe Deletion**: Remove large files and directories directly from the interface — with confirmation prompts.
- 💾 **Export to JSON**: Save scan results for further analysis or batch operations.
- ⚡ **Real-Time Feedback**: Live progress indicators and graceful handling of permission issues.
- 🛡️ **Actual Privacy**: 100% offline. No telemetry, no analytics, no tracking - can't even check for updates.

---

https://github.com/user-attachments/assets/1aae04e7-3201-414d-a1e3-6ea5d55bd691

---

## 📦 Installation

### Prerequisites
- Python 3.8+
- pip (Python package installer)
- (Optional but recommended) Use a virtual environment

### Install via pip (preferred)
```bash
pip install reclaimed
```

### Install via Homebrew (macOS)
```bash
brew install taylorwilsdon/tap/reclaimed
```

### Install from Source
```bash
git clone https://github.com/taylorwilsdon/reclaimed.git
cd reclaimed
pip install -e .
```

For development:
```bash
pip install -r requirements.txt
```

---

## 🚀 Usage

### Basic
```bash
reclaimed ~/Documents
```

### Advanced
```bash
# Show more results
reclaimed ~/Documents --files 20 --dirs 15

# Save results to JSON
reclaimed ~/Documents --output results.json
```

### Options
| Option | Description |
|:------|:------------|
| `PATH` | Directory to scan (default: current directory) |
| `-f, --files N` | Number of largest files to show (default: 10) |
| `-d, --dirs N` | Number of largest directories to show (default: 10) |
| `-o, --output FILE` | Save results to a JSON file |
| `-i, --interactive` | Launch the interactive Textual UI |

---

## 📊 Output

### CLI Mode
- Real-time progress indicator (files scanned, total size)
- Tables of largest files and directories
- iCloud vs local storage clearly indicated
- Summary of any access issues

### Interactive Mode
- Tabbed interface: switch between Files and Directories
- Keyboard navigation (arrow keys) and mouse support
- Sort items by size, name, or path
- Delete files/directories with confirmation
- Refresh scan results

---

## 🎛️ Interactive Mode

Launch automatically or with `-i` / `--interactive`:

```bash
reclaimed ~/Documents -i
```

Non-interactive mode (minimal output) can be forced with:

```bash
reclaimed ~/Documents --no-interactive
```

### Keyboard Shortcuts

| Key        | Action                      |
|------------|------------------------------|
| `F`        | Switch to Files view          |
| `D`        | Switch to Directories view    |
| `S`        | Sort items                    |
| `R`        | Refresh scan                  |
| `Delete`   | Delete selected item          |
| `?`        | Show help                     |
| `Q`        | Quit application              |
| Arrow keys | Navigate through items        |

---

## 🛠️ Development

This project uses [UV](https://github.com/astral-sh/uv) for building/publishing and [Hatch](https://hatch.pypa.io/) for workflow management.

### Setup Development Environment
```bash
pip install -r requirements.txt
hatch shell
```

### Common Commands
```bash
# Run tests
hatch test

# Build distribution packages
uv build --sdist --wheel

# Create a new release
./release.sh

# Run interactively
python -m reclaimed /path/to/scan
```

---

## 🤝 Contributing

Contributions are welcome!  
Please see the [Contributing Guide](CONTRIBUTING.md) for details.

---

## 📜 License

This project is licensed under the **MIT License**.  
See the [LICENSE](LICENSE) file for full details.

---

<p align="center">
  <sub>Built with ❤️ for those who love clean disks and clean code.</sub>
</p>
