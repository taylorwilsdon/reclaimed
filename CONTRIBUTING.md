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

Releases are automated through GitHub Actions when tags are pushed:

1. Ensure all tests pass on main
2. Tag the release:
   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0"
   ```
3. Push tags:
   ```bash
   git push --tags
   ```

The GitHub Action will automatically:
- Run all tests
- Build the package
- Publish to PyPI

## Questions?

Feel free to open an issue for any questions or concerns.

Thank you for contributing to reclaimed! 🌟
