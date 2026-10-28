"""UI discovery must never reach the owner's local inference server in tests."""
import logging
import os
import tempfile
from pathlib import Path

import pytest


# Collection imports backend modules, so reserve a disposable root before any
# test module binds persistence paths. Every worker gets its own collection root.
_collection_root = tempfile.TemporaryDirectory(prefix=f"aotn-pytest-{os.getpid()}-")
os.environ['AOTN_DATA_DIR'] = str(Path(_collection_root.name) / 'data')
os.environ['HERMES_HOME'] = str(Path(_collection_root.name) / 'hermes')


@pytest.fixture(autouse=True)
def isolated_test_data(tmp_path, monkeypatch):
    """One real data root per test, including import-bound directory aliases.

    Specific test fixtures may replace these with narrower paths afterwards.
    Subprocesses inherit the test root unless they explicitly exercise --data-dir.
    """
    from backend import persistence, configuration_manager, error_handler
    from backend import output_manager, run_history, logging_setup

    data = tmp_path / 'aotn-data'
    monkeypatch.setenv('AOTN_DATA_DIR', str(data))
    monkeypatch.setenv('HERMES_HOME', str(tmp_path / 'hermes'))
    monkeypatch.setattr(persistence, 'DATA_DIR', data)
    for field in ('WORKFLOWS_DIR', 'RUN_HISTORY_DIR', 'RUN_ERRORS_DIR', 'SETTINGS_DIR',
                  'RUN_OUTPUTS_DIR', 'SECRETS_DIR', 'LOGS_DIR', 'RUN_FILES_DIR', 'STASH_DIR'):
        monkeypatch.setattr(persistence, field, data / field.removesuffix('_DIR').lower())
    for module, field in ((configuration_manager, 'SETTINGS_DIR'),
                          (error_handler, 'RUN_ERRORS_DIR'),
                          (output_manager, 'RUN_OUTPUTS_DIR'),
                          (run_history, 'RUN_HISTORY_DIR'), (logging_setup, 'LOGS_DIR')):
        monkeypatch.setattr(module, field, getattr(persistence, field))
    yield data


@pytest.fixture(autouse=True)
def restore_logging_handlers():
    """TUI/CLI logging setup must not leave handlers tied to an old capture."""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    for handler in root.handlers[:]:
        if handler not in handlers:
            handler.close()
    root.handlers[:] = handlers
    root.setLevel(level)



@pytest.fixture(autouse=True)
def isolated_model_picker_discovery(monkeypatch):
    async def unavailable(*args, **kwargs):
        raise ConnectionError('No fake discovery server configured')
    monkeypatch.setattr('frontend.widgets.local_model_picker.list_models', unavailable)
