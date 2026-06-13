# Contributing Guide

Thank you for your interest in contributing to **pyyunoheat**! This document provides instructions for setting up a local development environment, adhering to code style guidelines, and running tests.

---

## Local Setup

### 1. Prerequisites
- Python 3.11 or higher.
- `git` installed on your machine.

### 2. Clone the Repository
Clone the project repository and navigate into the project directory:
```bash
git clone https://github.com/Irishsmurf/pyyunoheat.git
cd pyyunoheat
```

### 3. Create a Virtual Environment
Initialize a virtual environment to isolate project dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 4. Install Dependencies
Install the package in editable mode along with development dependencies:
```bash
pip install -e ".[dev]"
```

---

## Code Quality and Style

We use **Ruff** for fast linting and formatting. Please run these tools before submitting changes.

### Running the Linter
To analyze your code for static errors, style violations, and imports sorting:
```bash
ruff check .
```

To automatically resolve fixable violations:
```bash
ruff check . --fix
```

### Running the Formatter
To format the entire codebase to match our style standards:
```bash
ruff format .
```

---

## Running Tests

Our test suite uses **pytest** and **pytest-asyncio** to validate behavior.

### Running the Suite
Execute the tests locally:
```bash
pytest -v
```

### Running a Specific Test File
Run tests inside a specific module:
```bash
pytest -v tests/test_light.py
```

### Writing Tests
- **Mocking HTTP Requests**: Since the library communicates with Keycloak and Tridens, do not perform live HTTP connections in unit tests. Use `aioresponses` to mock API endpoints.
- **Token Isolation**: Use `InMemoryTokenStore` in tests to prevent reading or writing files to the local user configuration directory (`~/.config/`).
- **Fixtures**: Put shared setups in `tests/conftest.py`.

---

## Contribution Workflow

1. **Create an Issue**: Open an issue to discuss major architectural changes or features before writing code.
2. **Branching**: Create a topic branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Commit Messages**: Write clear, descriptive commit messages.
4. **Push & Pull Request**: Push your branch to GitHub and open a Pull Request (PR) against the `main` branch. Ensure the test suite passes and code is formatted.
