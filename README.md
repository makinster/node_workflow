# Attack of the Nodes

A node-based workflow engine with a Textual terminal UI. Build, run, branch, and inspect pipelines entirely from the terminal.

## Requirements

- Python 3.12 or later (developed on 3.14)
- Git

## Setup

```bash
git clone <repo-url>
cd node_workflow

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
.venv\Scripts\Activate.ps1         # Windows PowerShell

# Install exact pinned dependencies, then install the project
pip install -r attackofthenodes_v05/requirements.lock
pip install -e attackofthenodes_v05/
```

## Run

```bash
aotn
```

That's it. No `cd` required after the initial setup.

## Run Tests

```bash
cd attackofthenodes_v05
pytest
```

## Development (live reload / Textual devtools)

```bash
cd attackofthenodes_v05
textual run --dev main.py
```

## Upgrading dependencies

When intentionally upgrading a package, regenerate the lock file:

```bash
pip install --upgrade textual
pip freeze > attackofthenodes_v05/requirements.lock
```
