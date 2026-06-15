"""Tests for SecretsManager and NodeContext.get_secret integration."""

import json
import pytest
from pathlib import Path

from backend.secrets_manager import SecretsManager
from backend.node_base import NodeContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manager(tmp_path: Path) -> SecretsManager:
    return SecretsManager(storage_dir=tmp_path)


def _secrets_file(tmp_path: Path) -> Path:
    return tmp_path / "secrets.json"


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------


def test_set_and_get_secret(tmp_path):
    sm = _make_manager(tmp_path)
    sm.set_secret("api_key", "abc123")
    assert sm.get_secret("api_key") == "abc123"


def test_get_missing_key_returns_none(tmp_path):
    sm = _make_manager(tmp_path)
    assert sm.get_secret("nonexistent") is None


def test_overwrite_existing_key(tmp_path):
    sm = _make_manager(tmp_path)
    sm.set_secret("token", "old")
    sm.set_secret("token", "new")
    assert sm.get_secret("token") == "new"


def test_delete_existing_key(tmp_path):
    sm = _make_manager(tmp_path)
    sm.set_secret("k", "v")
    assert sm.delete_secret("k") is True
    assert sm.get_secret("k") is None


def test_delete_missing_key_returns_false(tmp_path):
    sm = _make_manager(tmp_path)
    assert sm.delete_secret("nope") is False


def test_has_key_true_and_false(tmp_path):
    sm = _make_manager(tmp_path)
    sm.set_secret("present", "yes")
    assert sm.has_key("present") is True
    assert sm.has_key("absent") is False


def test_list_keys_sorted(tmp_path):
    sm = _make_manager(tmp_path)
    sm.set_secret("z_key", "1")
    sm.set_secret("a_key", "2")
    sm.set_secret("m_key", "3")
    assert sm.list_keys() == ["a_key", "m_key", "z_key"]


def test_list_keys_empty(tmp_path):
    sm = _make_manager(tmp_path)
    assert sm.list_keys() == []


# ---------------------------------------------------------------------------
# Persistence — round-trip through disk
# ---------------------------------------------------------------------------


def test_persists_to_disk(tmp_path):
    sm = _make_manager(tmp_path)
    sm.set_secret("pw", "secret!")
    raw = _secrets_file(tmp_path).read_text(encoding="utf-8")
    data = json.loads(raw)
    assert data["pw"] == "secret!"


def test_loads_from_existing_file(tmp_path):
    path = _secrets_file(tmp_path)
    path.write_text(json.dumps({"preloaded": "value"}), encoding="utf-8")
    sm = _make_manager(tmp_path)
    assert sm.get_secret("preloaded") == "value"


def test_lazy_load_only_once(tmp_path):
    path = _secrets_file(tmp_path)
    path.write_text(json.dumps({"k": "first"}), encoding="utf-8")
    sm = _make_manager(tmp_path)
    _ = sm.get_secret("k")  # triggers load
    # overwrite file externally — should NOT be visible until reload
    path.write_text(json.dumps({"k": "changed"}), encoding="utf-8")
    assert sm.get_secret("k") == "first"


def test_reload_refreshes_from_disk(tmp_path):
    path = _secrets_file(tmp_path)
    path.write_text(json.dumps({"k": "first"}), encoding="utf-8")
    sm = _make_manager(tmp_path)
    _ = sm.get_secret("k")  # load
    path.write_text(json.dumps({"k": "updated"}), encoding="utf-8")
    sm.reload()
    assert sm.get_secret("k") == "updated"


def test_missing_file_starts_empty(tmp_path):
    sm = _make_manager(tmp_path)
    assert sm.list_keys() == []
    # no crash, no file required
    assert _secrets_file(tmp_path).exists() is False


def test_invalid_json_starts_empty(tmp_path):
    path = _secrets_file(tmp_path)
    path.write_text("NOT JSON", encoding="utf-8")
    sm = _make_manager(tmp_path)
    assert sm.list_keys() == []


def test_non_dict_json_starts_empty(tmp_path):
    path = _secrets_file(tmp_path)
    path.write_text(json.dumps(["a", "b"]), encoding="utf-8")
    sm = _make_manager(tmp_path)
    assert sm.list_keys() == []


# ---------------------------------------------------------------------------
# NodeContext integration
# ---------------------------------------------------------------------------


def _minimal_context(secrets_manager=None) -> NodeContext:
    """Build a NodeContext with only the secrets_manager wired (rest are stubs)."""
    return NodeContext(
        node_id="test_node",
        branch_id="main",
        run_id="run_1",
        inputs={},
        memory_bank=None,  # type: ignore[arg-type]
        signal_done=lambda _: None,
        signal_error=lambda _: None,
        signal_waiting_for_input=None,  # type: ignore[arg-type]
        wait_for_nodes=None,  # type: ignore[arg-type]
        wait_for_merge=None,  # type: ignore[arg-type]
        secrets_manager=secrets_manager,
    )


def test_context_get_secret_returns_value(tmp_path):
    sm = _make_manager(tmp_path)
    sm.set_secret("openai_key", "sk-test")
    ctx = _minimal_context(secrets_manager=sm)
    assert ctx.get_secret("openai_key") == "sk-test"


def test_context_get_secret_none_when_no_manager():
    ctx = _minimal_context(secrets_manager=None)
    assert ctx.get_secret("anything") is None


def test_context_get_secret_none_when_key_missing(tmp_path):
    sm = _make_manager(tmp_path)
    ctx = _minimal_context(secrets_manager=sm)
    assert ctx.get_secret("does_not_exist") is None
