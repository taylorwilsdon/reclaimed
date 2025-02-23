# reclaim 🌟

A powerful and user-friendly command-line tool for analyzing disk usage, with special handling for iCloud storage on macOS. Quickly find your largest files and directories with a beautiful, color-coded interface. I let aider write the README.md boilerplate and it's all accurate but I'm still not sure how we feel about the emojis... it seems Claude is a colorful gentleman when writing markdown.

![Disk Scanner Demo](demo.gif)

<img width="898" alt="image" src="https://github.com/user-attachments/assets/b8c87581-978b-46e4-bf8b-d9e9b2cd5f9b" />

## Features

- 🚀 Fast recursive directory scanning, legitimately performant and batches progress updates efficently 
- ☁️ Smart detection of iCloud vs local storage which is nice on the macbook
- 📊 She pretty (it utilizes the [Textualize/rich](https://github.com/Textualize/rich) library for fancy CLI stylings)
- 💾 Export results to JSON for further analysis or batch operations
- ⚡️ Real-time progress indication actually great
- 🛡️ Graceful handling of permission issues, doesn't freeze like the old diskinventoryx

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Technically not a venv but if you aren't using a venv you're generally doing python wrong

### Using pip

```bash
pip install reclaim
```

### From Source

```bash
git clone https://github.com/taylorwilsdon/reclaim.git
cd reclaim
pip install -e .
```

## Usage

Basic usage:
```bash
reclaim ~/Documents
```

Advanced options:
```bash
# Show more results
reclaim ~/Documents --files 20 --dirs 15

# Save results to JSON
reclaim ~/Documents --output results.json
```

### Options

- `PATH`: Directory to scan (default: current directory)
- `-f, --files N`: Number of largest files to show (default: 10)
- `-d, --dirs N`: Number of largest directories to show (default: 10)
- `-o, --output FILE`: Save results to JSON file

## Output

The tool provides:
- A real-time progress indicator showing files scanned and total size
- Two tables showing the largest files and directories
- Clear indication of iCloud vs local storage
- Summary of any access issues encountered

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
