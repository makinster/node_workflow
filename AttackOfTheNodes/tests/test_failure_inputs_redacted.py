"""Failed-node inputs persisted in run_errors are redacted and capped (PR #125 review)."""

from __future__ import annotations

import asyncio
from copy import deepcopy
import json

import pytest

from backend import persistence
from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.run_policies import TerminatePolicy
from backend.run_service import RunService
from backend.secrets_manager import SecretsManager
from backend.workflow_map import WorkflowMap


CANARY = "CANARY-sk-7f3a9e21-never-on-disk"
LOGGED_INPUT_CHARS = 2000  # backend.supervisor's cap; literal so the test runs on older heads


@pytest.fixture(autouse=True)
def records(tmp_path, monkeypatch):
    from backend import error_handler, output_manager, run_history

    monkeypatch.setattr(error_handler, "RUN_ERRORS_DIR", tmp_path / "run_errors")
    monkeypatch.setattr(run_history, "RUN_HISTORY_DIR", tmp_path / "run_history")
    monkeypatch.setattr(output_manager, "RUN_OUTPUTS_DIR", tmp_path / "run_outputs")
    monkeypatch.setattr(persistence, "SECRETS_DIR", tmp_path / "secrets")
    SecretsManager().set_secret("api_key", CANARY)
    return tmp_path


async def run_after_start(tmp_path, node_type, greeting, *, structured=False):
    wm = WorkflowMap(NodeFactory(), EventBus())
    wm.create_new("Failure inputs")
    start = wm.add_node("start_node", alias="Start")
    wm.update_node_config(start, {"rows": [dict(id="payload", name="payload", type="var",
        value=greeting, required=True, to="Downstream")]} if structured else {"greeting": greeting})
    failing = wm.add_node(node_type, alias="Fails")
    wm.connect(start, "default", failing, "input")
    end = wm.add_node("end_node", alias="End")
    wm.connect(failing, "default", end, "input")
    path = tmp_path / "wf.json"
    path.write_text(json.dumps(wm.get_workflow_data_for_save()), encoding="utf-8")
    service = RunService.create()
    service.load(str(path))
    await service.start(recovery_policy=TerminatePolicy("terminate_branch"))
    result = await asyncio.wait_for(service.wait(), 10)
    assert result.errors, "the node was expected to fail"
    files = list((tmp_path / "run_errors").glob("*.json"))
    assert files, "the failure was expected to be persisted"
    return "".join(f.read_text(encoding="utf-8") for f in files), files


async def test_check_workflow_spec_failure_keeps_draft_secret_off_disk(records):
    draft = json.dumps({
        "format": "aotn-workflow/1", "name": "Draft",
        "nodes": {"start": {"type": "start_node"},
                  "end": {"type": "end_node", "config": {"unknown_field": CANARY}}},
        "connections": [{"from": "start.default", "to": "end.input"}],
    })
    text, _ = await run_after_start(records, "check_workflow_spec_node", draft)
    assert "spec_invalid" in text
    assert CANARY not in text
    assert "[redacted]" in text


async def test_any_failing_node_input_is_redacted_and_trimmed(records):
    greeting = f"token {CANARY} Authorization: Bearer abc123xyz " + "x" * 5000
    text, files = await run_after_start(records, "error_node", greeting)
    assert CANARY not in text and "abc123xyz" not in text
    record = json.loads(files[0].read_text(encoding="utf-8"))
    entries = record if isinstance(record, list) else record.get("errors", [record])
    logged = entries[0]["context"]["inputs"]["input"]
    assert len(logged) < LOGGED_INPUT_CHARS + 80
    assert "[trimmed: " in logged


@pytest.mark.parametrize("payload,credentials", [
    ({"api_key": "fresh-token", "password": "fresh-password", "note": "keep this fact"},
     ["fresh-token", "fresh-password"]),
    ({"password": ["first-password", {"value": "second-password"}], "note": "keep this fact"},
     ["first-password", "second-password"]),
    ({"nested": {"api_key": "nested-token"}, "accounts": [
        {"password": "list-password", "note": "keep this fact"},
        {"deeper": [{"AWS_SECRET_ACCESS_KEY": "nested-list-secret"}]}]},
     ["nested-token", "list-password", "nested-list-secret"]),
])
async def test_structured_credentials_never_reach_saved_error(records, payload, credentials):
    # Deliberately absent from Secrets: only the shared sensitive-label rules
    # can recognize these credentials. Exercise the real engine and disk record.
    original = deepcopy(payload)
    text, files = await run_after_start(records, "error_node", payload, structured=True)
    assert all(credential not in text for credential in credentials)
    record = json.loads(files[0].read_text(encoding="utf-8"))
    entries = record if isinstance(record, list) else record.get("errors", [record])
    logged = entries[0]["context"]["inputs"]["input"]
    assert "[redacted]" in json.dumps(logged)
    assert "keep this fact" in json.dumps(logged)
    assert payload == original, "logging must not mutate the live payload"


async def test_structured_redaction_preserves_leaf_rules_known_values_and_cap(records):
    payload = {"note": "Authorization: Bearer unlisted-inline-token", "known": CANARY,
               "padding": "x" * 5000,
               "tail": [{"api_key": "token-after-the-cap"}]}
    text, files = await run_after_start(records, "error_node", payload, structured=True)
    assert all(value not in text for value in [CANARY, "unlisted-inline-token", "token-after-the-cap"])
    record = json.loads(files[0].read_text(encoding="utf-8"))
    entries = record if isinstance(record, list) else record.get("errors", [record])
    logged = entries[0]["context"]["inputs"]["input"]
    assert len(logged) < LOGGED_INPUT_CHARS + 80
    assert "[trimmed: " in logged


def test_structured_keys_are_masked_after_labels_and_plain_context_stays_structured(records):
    from backend.supervisor import _logged_inputs
    manager = SecretsManager()
    manager.set_secret("label-canary", "api_key")
    payload = {"api_key": "unlisted-key-value", "ordinary": {"not-password": "public fact"}}
    original = deepcopy(payload)
    safe = _logged_inputs({"input": payload}, manager)
    assert "unlisted-key-value" not in json.dumps(safe)
    assert "api_key" not in json.dumps(safe)
    assert "public fact" in json.dumps(safe)
    assert payload == original
    benign = {"input": [{"not-password": "public fact", "count": 3, "ready": True}]}
    assert _logged_inputs(benign, manager) == benign
