# reclaim 🌟

A powerful and user-friendly command-line tool for analyzing disk usage, with special handling for iCloud storage on macOS. Quickly find your largest files and directories with a beautiful, color-coded interface.

![Disk Scanner Demo](demo.gif)

## Features

- 🚀 Fast recursive directory scanning
- ☁️ Smart detection of iCloud vs local storage
- 📊 Beautiful color-coded output using Rich
- 💾 Export results to JSON for further analysis
- ⚡️ Real-time progress indication
- 🛡️ Graceful handling of permission issues

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Using pip

```bash
pip install reclaim
```

### From Source

```bash
git clone https://github.com/taylorwilsdon/reclaim.git
cd reclaim
pip install -r requirements.txt
hatch shell
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
```

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
