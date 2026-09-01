# Contributing to reclaimed

Thank you for your interest in contributing to reclaimed! This document provides guidelines and instructions for contributing.

## Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/yourusername/reclaimed.git
   cd reclaimed
   ```

2. Create a development environment and install the project with its dev
   dependencies. `pyproject.toml` is the single authoritative dependency list:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -e ".[dev]"
   ```

## Development Workflow

1. Create a new branch for your feature:
   ```bash
   git checkout -b feature-name
   ```

2. Make your changes and ensure all tests pass:
   ```bash
   pytest
   ```

3. Run the full test suite with coverage:
   ```bash
   pytest --cov=reclaimed --cov-report=term-missing
   ```

4. Run linting and type checks:
   ```bash
   ruff check .
   black --check .
   mypy reclaimed
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

Releases are managed through `scripts/release.py`:

```bash
python3 scripts/release.py
```

The script prompts for the next version, then:

- Checks for git, uv, and gh, a clean working tree, gh auth, and a free tag
- Resolves a PyPI token before anything irreversible happens (see below)
- Bumps `reclaimed/version.py`, builds the sdist and wheel with UV
- Commits, tags, and pushes
- Uploads to PyPI and opens a draft GitHub release with the artifacts attached
- Re-pins `homebrew/reclaimed.rb` to the new tag and to the dependency
  versions UV resolves, then commits and pushes that formula update

The PyPI token is read from `$PYPI_TOKEN` (or `$UV_PUBLISH_TOKEN`,
`$PYPI_API_TOKEN`, `$TWINE_PASSWORD`), then from `.env` in the repo root, then
from `~/.pypirc`. If none of those has one, the script prompts for it and
offers to save it to `.env`, which is gitignored.

Useful flags: `--bump {patch,minor,major}` or `--version X.Y.Z` to skip the
prompt, `--skip-pypi`, `--skip-homebrew`, `--no-browser`, and `-y`.

To refresh only the Homebrew formula's dependency pins, without releasing:

```bash
python3 scripts/release.py --homebrew-only
```

The formula update is left uncommitted in that mode.

After a release, publish to Homebrew:

- Ensure you have a tap repository at github.com/yourusername/homebrew-tap
- Copy homebrew/reclaimed.rb to your tap repository
- Users can then install with: `brew install yourusername/tap/reclaimed`

## Questions?

Feel free to open an issue for any questions or concerns.

Thank you for contributing to reclaimed! 🌟
