"""The harness must isolate reused ids across tests, workers and subprocesses."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize('value', ['first', 'second'])
def test_reused_workflow_and_settings_names_are_test_local(isolated_test_data, value):
    from backend import persistence, configuration_manager, error_handler
    from backend import output_manager, run_history, logging_setup, hermes_folder
    from backend.configuration_manager import ConfigurationManager

    root = isolated_test_data
    assert Path(os.environ['AOTN_DATA_DIR']) == root
    for name in ('WORKFLOWS_DIR', 'SETTINGS_DIR', 'RUN_HISTORY_DIR', 'RUN_OUTPUTS_DIR',
                 'RUN_ERRORS_DIR', 'RUN_FILES_DIR', 'SECRETS_DIR', 'STASH_DIR', 'LOGS_DIR'):
        assert getattr(persistence, name).is_relative_to(root)
    for module, name in ((configuration_manager, 'SETTINGS_DIR'), (error_handler, 'RUN_ERRORS_DIR'),
                         (output_manager, 'RUN_OUTPUTS_DIR'), (run_history, 'RUN_HISTORY_DIR'),
                         (logging_setup, 'LOGS_DIR')):
        assert getattr(module, name) == getattr(persistence, name)
    assert not persistence.workflow_exists('same-id')
    persistence.save_workflow('same-id', {'name': value})
    settings = ConfigurationManager()
    assert settings.get('hermes_send_to_names') != value
    settings.set('hermes_send_to_names', value)
    assert ConfigurationManager().get('hermes_send_to_names') == value
    assert hermes_folder.folder().is_relative_to(root.parent)
    result = subprocess.run([sys.executable, '-c',
        "from backend import persistence as p,hermes_folder as h;import json;"
        "print(json.dumps([str(p.DATA_DIR),p.load_workflow('same-id')['name'],str(h.folder())]))"],
        capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == [str(root), value, str(hermes_folder.folder())]
