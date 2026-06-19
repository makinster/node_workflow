"""Tests for the canonical data-type vocabulary (backend/data_types.py).

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_data_types.py -v
"""

import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend import data_types as dt
from backend.data_types import (
    CANONICAL_TYPES,
    DEFAULT_TYPE,
    REFERENCE_TYPES,
    DataType,
    UnknownDataTypeWarning,
)


def test_canonical_set_is_exactly_the_handoff_starting_set():
    # Handoff §5: string, number, bool, var, file, ai_session, any.
    assert CANONICAL_TYPES == {
        "string",
        "number",
        "bool",
        "var",
        "file",
        "ai_session",
        "any",
    }
    # The enum and the frozenset agree.
    assert CANONICAL_TYPES == {member.value for member in DataType}

    print("test_canonical_set_is_exactly_the_handoff_starting_set PASSED")


def test_bool_is_canonical_spelling_not_boolean():
    # Reconciliation: §5 wins, canonical spelling is "bool".
    assert "bool" in CANONICAL_TYPES
    assert "boolean" not in CANONICAL_TYPES
    # "boolean" survives only as a deprecated alias that canonicalizes to "bool".
    assert dt.canonicalize("boolean") == "bool"
    assert dt.is_valid_type("boolean")  # alias resolves, no error

    print("test_bool_is_canonical_spelling_not_boolean PASSED")


def test_membership_and_validation():
    for name in CANONICAL_TYPES:
        assert dt.is_valid_type(name)
        assert dt.validate_type(name) is True
    assert not dt.is_valid_type("widget")
    assert not dt.is_valid_type("text_small")  # explicitly not a type (§2)

    print("test_membership_and_validation PASSED")


def test_reference_types():
    assert REFERENCE_TYPES == {"file", "ai_session"}
    assert dt.is_reference_type("file")
    assert dt.is_reference_type("ai_session")
    assert not dt.is_reference_type("string")
    assert not dt.is_reference_type("any")

    print("test_reference_types PASSED")


def test_any_is_explicit_permissive_default():
    assert DEFAULT_TYPE == "any"
    assert "any" in CANONICAL_TYPES
    # Absent / empty type resolves to the explicit "any", never a silent untyped.
    assert dt.coerce_type(None) == "any"
    assert dt.coerce_type("") == "any"
    assert dt.coerce_type("number") == "number"
    assert dt.coerce_type("boolean") == "bool"  # alias coercion

    print("test_any_is_explicit_permissive_default PASSED")


def test_unknown_type_emits_warning():
    with pytest.warns(UnknownDataTypeWarning):
        result = dt.validate_type("mystery")
    assert result is False

    # The source label is folded into the message for actionability.
    with pytest.warns(UnknownDataTypeWarning, match="my_port"):
        dt.validate_type("mystery", source="my_port")

    print("test_unknown_type_emits_warning PASSED")


def test_canonical_types_do_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error", UnknownDataTypeWarning)
        for name in CANONICAL_TYPES:
            assert dt.validate_type(name) is True
        # Deprecated alias resolves silently too.
        assert dt.validate_type("boolean") is True

    print("test_canonical_types_do_not_warn PASSED")


def test_vault_and_port_lists_agree():
    # Single source of truth: typed vault-entry types and port data types are
    # the same vocabulary, so dropdown filtering between them is coherent.
    assert dt.vault_entry_types() == dt.port_data_types()
    assert dt.vault_entry_types() == CANONICAL_TYPES

    print("test_vault_and_port_lists_agree PASSED")


def test_unknown_types_helper():
    assert dt.unknown_types(["string", "widget", "bool", "blob"]) == ["widget", "blob"]
    assert dt.unknown_types(CANONICAL_TYPES) == []

    print("test_unknown_types_helper PASSED")
