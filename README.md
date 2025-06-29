# reclaimed ♻️

<p align="center">
  <img src="https://img.shields.io/github/license/taylorwilsdon/reclaimed?style=flat&logo=github&logoColor=white&label=License&labelColor=555&color=blue" alt="License" />
  <a href="https://github.com/taylorwilsdon">
    <img src="https://img.shields.io/badge/Privacy-100%25_Client--Side_Processing-blue?style=flat&logo=shield&logoColor=white&labelColor=555" alt="Privacy Shield" />
  </a>
  <img src="https://img.shields.io/pypi/v/reclaimed?style=flat&logo=pypi&logoColor=white&label=Version&labelColor=005da7&color=blue" alt="PyPI Version" />
  <a href="https://pepy.tech/projects/reclaimed"><img src="https://static.pepy.tech/badge/reclaimed" alt="PyPI Downloads"></a>
</p>

<div align="center">
 <img width="50%" src="https://github.com/user-attachments/assets/7f02903b-24ca-4415-a929-5a8f89caa99d" />
</div>

---

**reclaimed** is a cross-platform, ultra-lightweight, and surprisingly powerful command-line tool for analyzing disk usage — with special handling for iCloud storage on macOS.  
Quickly find your largest files and directories with a beautiful, color-coded interface, and manage them through an interactive terminal UI.  
Fully supports **Linux**, **macOS**, and **Windows**.

---

### A quick plug for AI-Enhanced Docs

> **This README was crafted with AI assistance, and here's why that matters**
> 
> As a solo developer building open source tools that may only ever serve my own needs, comprehensive documentation often wouldn't happen without AI help. Using agentic dev tools like **Roo** & **Claude Code** that understand the entire codebase, AI doesn't just regurgitate generic content - it extracts real implementation details and creates accurate, specific documentation.
>
> In this case, Sonnet 4 took a pass & a human (me) verified them 6/28/25.

---

## ✨ Features

- 🚀 **Legitimately Performant**: Fast recursive directory scanning with ultra-efficient progress updates.
  - Carefully tuned repaint frequency — optimized to avoid slowing results by even 5ms.
  - Separate thread for the clock to keep real-time updates buttery smooth.
- ☁️ **iCloud Aware**: Detects and handles iCloud Drive symlink files vs local storage (macOS).
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

### uvx (fastest)
```bash
uvx reclaimed
```

### Install via pip
```bash
pip install reclaimed
```

### Install via Homebrew (macOS)
```bash
brew install taylorwilsdon/tap/reclaimed
```

### Build from Source
```bash
git clone https://github.com/taylorwilsdon/reclaimed.git
cd reclaimed
pip install -e .
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

## 🎛️ Interactive Mode

Interactive mode is on by default. Non-interactive mode (minimal output) can be forced with:

```bash
reclaimed ~/Documents --no-interactive
```

### Keyboard Shortcuts
| Key | Action | | Key | Action |
|-----|--------|-|-----|--------|
| `F` | Files view | | `Delete` | Remove item |
| `D` | Directories view | | `R` | Refresh scan |
| `S` | Sort items | | `Q` | Quit |

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
