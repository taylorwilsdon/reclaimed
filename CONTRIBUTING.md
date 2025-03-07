# Contributing to reclaimed

Thank you for your interest in contributing to reclaimed! This document provides guidelines and instructions for contributing.

## Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/yourusername/reclaimed.git
   cd reclaimed
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a development environment:
   ```bash
   hatch shell
   ```

## Development Workflow

1. Create a new branch for your feature:
   ```bash
   git checkout -b feature-name
   ```

2. Make your changes and ensure all tests pass:
   ```bash
   hatch run test
   ```

3. Run the full test suite with coverage:
   ```bash
   hatch run test-cov
   ```

4. Run linting checks:
   ```bash
   hatch run lint
   ```

5. Commit your changes:
   ```bash
   git add .
   git commit -m "Description of changes"
   ```

6. Push to your fork:
   ```bash
   git push origin feature-name
   ```

7. Open a Pull Request

## Code Style

- We use Black for code formatting
- Ruff for linting
- MyPy for type checking
- All code must be type-annotated
- Maximum line length is 100 characters
- Follow PEP 8 guidelines

## Testing

- Write tests for all new features
- Maintain or improve code coverage
- Tests should be clear and meaningful
- Use pytest fixtures when appropriate

## Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in the present tense
- Keep the first line under 50 characters
- Add details in the commit body if needed

## Pull Requests

- Reference any related issues
- Include a clear description of changes
- Update documentation if needed
- Ensure all checks pass
- Keep changes focused and atomic

## Release Process

Releases are managed through the `release.sh` script:

1. Update the version in `reclaimed/version.py`

2. Run the release script:
   ```bash
   ./release.sh
   ```

   This script will:
   - Check for required tools (jq)
   - Ensure you're on the main branch
   - Clean previous build artifacts
   - Build the package with UV
   - Create and push git tags
   - Create a GitHub release
   - Update the Homebrew formula with the correct SHA and dependencies
   - Prompt to publish to PyPI

3. To update only the Homebrew formula dependencies:
   ```bash
   ./release.sh --update-deps-only
   ```

4. After running the script, publish to Homebrew:
   - Ensure you have a tap repository at github.com/yourusername/homebrew-tap
   - Copy homebrew/reclaimed.rb to your tap repository
   - Users can then install with: `brew install yourusername/tap/reclaimed`

## Questions?

Feel free to open an issue for any questions or concerns.

Thank you for contributing to reclaimed! 🌟
