"""Canonical data-type vocabulary for AttackOfTheNodes.

Single source of truth for the coarse data-type identities shared by **node
port data types** and **typed vault-entry types**. Before this module the two
sides used independent free strings, which drift and break the dropdown
type-filtering that pairs compatible upstream ports with vault keys during
config (see ``NODE_STANDARDS.md`` "Typed Vault Outputs" and
``NODE_STANDARDIZATION_HANDOFF.md`` §5).

Canonical set: ``string``, ``number``, ``bool``, ``var``, ``file``,
``ai_session``, ``any``.

- ``any`` is an **explicit, permissive** type. There is no silent "untyped"
  default; a port or vault entry that omits a type is treated as ``any`` only
  because :data:`DEFAULT_TYPE` says so explicitly.
- ``file`` and ``ai_session`` are **reference types**: the stored value is a
  string ref key; the real Python handle lives in ``RunSession`` and is
  retrieved with ``context.run_session.get_resource(ref_key)``.

This is a semantic / UX convention, not a hard runtime type — runtime data is
JSON plus refs. The vocabulary drives (a) dropdown filtering of compatible
upstream ports / vault keys during config and (b) optional soft validation
warnings. The node helper consumes :func:`validate_type` to warn authors about
unknown type strings.

**Reconciliation note (2026-06-19).** The earlier typed-vault decision spelled
the boolean type ``boolean`` while the §5 port set uses ``bool``. Per the
handoff (§5 is authoritative) the canonical spelling is **``bool``**.
``boolean`` is retained only as a deprecated alias (see :data:`LEGACY_ALIASES`)
so older specs and saved workflows still resolve; :func:`canonicalize` maps it
to ``bool``.
"""

from __future__ import annotations

import warnings
from enum import Enum
from typing import FrozenSet, Iterable


class DataType(str, Enum):
    """Canonical data-type identities, shared by ports and vault entries."""

    STRING = "string"
    NUMBER = "number"
    BOOL = "bool"
    VAR = "var"
    FILE = "file"
    AI_SESSION = "ai_session"
    ANY = "any"


#: Every canonical type string. Both port data types and vault-entry types draw
#: from this one set — there is no parallel vocabulary.
CANONICAL_TYPES: FrozenSet[str] = frozenset(dt.value for dt in DataType)

#: Reference types: the stored value is a ref key; the handle lives in
#: ``RunSession``.
REFERENCE_TYPES: FrozenSet[str] = frozenset(
    {DataType.FILE.value, DataType.AI_SESSION.value}
)

#: The explicit permissive type. Used as the documented default when a port or
#: vault entry declares no type (absent ``data_type`` ⇒ ``any``, per handoff §6).
DEFAULT_TYPE: str = DataType.ANY.value

#: Deprecated spellings mapped to their canonical form. ``boolean`` predates the
#: §5 reconciliation that fixed the canonical spelling at ``bool``.
LEGACY_ALIASES: dict[str, str] = {
    "boolean": DataType.BOOL.value,
}


class UnknownDataTypeWarning(UserWarning):
    """Raised (via :mod:`warnings`) when a type string is not canonical."""


def canonicalize(type_name: str) -> str:
    """Return the canonical spelling for *type_name*.

    Applies :data:`LEGACY_ALIASES` (e.g. ``boolean`` -> ``bool``). Unknown
    strings are returned unchanged so callers can detect and warn on them.
    """
    return LEGACY_ALIASES.get(type_name, type_name)


def is_valid_type(type_name: str) -> bool:
    """Return ``True`` if *type_name* is (or aliases to) a canonical type."""
    return canonicalize(type_name) in CANONICAL_TYPES


def is_reference_type(type_name: str) -> bool:
    """Return ``True`` if *type_name* is a RunSession-backed reference type."""
    return canonicalize(type_name) in REFERENCE_TYPES


def validate_type(type_name: str, *, source: str = "") -> bool:
    """Validate a type string, warning on unknown types.

    Helper-facing surface: the node helper calls this so authors get a warning
    rather than silent drift when a spec names a type outside the canonical
    vocabulary. Returns ``True`` for canonical types (including deprecated
    aliases, which resolve silently); returns ``False`` and emits an
    :class:`UnknownDataTypeWarning` for anything else.

    *source* is an optional label (node type, port name, vault key) folded into
    the warning to make it actionable.
    """
    if is_valid_type(type_name):
        return True
    where = f" for {source}" if source else ""
    warnings.warn(
        f"Unknown data type {type_name!r}{where}; expected one of "
        f"{sorted(CANONICAL_TYPES)}",
        UnknownDataTypeWarning,
        stacklevel=2,
    )
    return False


def coerce_type(type_name: str | None) -> str:
    """Return a canonical type, falling back to :data:`DEFAULT_TYPE`.

    ``None`` or empty resolves to ``any`` (the explicit permissive default).
    Known aliases are canonicalized; genuinely unknown strings are returned
    canonicalized-but-unchanged for the caller to validate/warn separately.
    """
    if not type_name:
        return DEFAULT_TYPE
    return canonicalize(type_name)


def port_data_types() -> FrozenSet[str]:
    """Canonical types valid as node port data types."""
    return CANONICAL_TYPES


def vault_entry_types() -> FrozenSet[str]:
    """Canonical types valid as typed vault-entry tags.

    Identical to :func:`port_data_types` — the two consumers share one
    vocabulary so dropdown filtering between ports and vault keys is coherent.
    """
    return CANONICAL_TYPES


def unknown_types(type_names: Iterable[str]) -> list[str]:
    """Return the subset of *type_names* that are not canonical (order-preserved)."""
    return [name for name in type_names if not is_valid_type(name)]


__all__ = [
    "DataType",
    "CANONICAL_TYPES",
    "REFERENCE_TYPES",
    "DEFAULT_TYPE",
    "LEGACY_ALIASES",
    "UnknownDataTypeWarning",
    "canonicalize",
    "is_valid_type",
    "is_reference_type",
    "validate_type",
    "coerce_type",
    "port_data_types",
    "vault_entry_types",
    "unknown_types",
]
