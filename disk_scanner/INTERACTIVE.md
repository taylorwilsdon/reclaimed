# Interactive Mode for Reclaim

Reclaim now includes an interactive mode powered by the Textual library, which provides a terminal-based UI for exploring and managing your files and directories.

## Getting Started

To launch the interactive mode, use the `-i` or `--interactive` flag:

```bash
python -m disk_scanner.cli /path/to/scan -i
```

## Features

### Navigation

- **Switch Views**: Toggle between Files and Directories views using the tabs or keyboard shortcuts:
  - Press `F` to view files
  - Press `D` to view directories

- **Navigate Tables**: Use arrow keys to move through the list of files or directories

### Actions

- **Delete Files/Directories**: Select an item and press `Delete` to remove it
  - A confirmation dialog will appear before deletion
  - For directories, all contents will be deleted recursively

- **Sort Items**: Press `S` to sort items by:
  - Size (largest first)
  - Name (alphabetically)
  - Path (alphabetically)

- **Refresh**: Press `R` to rescan the directory and update the display

- **Help**: Press `?` to view keyboard shortcuts and help information

- **Quit**: Press `Q` to exit the application

## Safety Features

- Confirmation is required before any deletion
- Warning is displayed when deleting directories
- Error handling for permission issues and other exceptions

## Requirements

The interactive mode requires the Textual library:

```bash
pip install textual
```

## Troubleshooting

If you encounter issues with the interactive mode:

1. Ensure Textual is installed correctly
2. Check terminal compatibility (most modern terminals are supported)
3. Fall back to standard CLI mode if needed
