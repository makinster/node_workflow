"""Stable codes for validator errors and warnings.

Every issue ``validate_workflow`` reports carries ``code`` (one of
:data:`ISSUE_CODES`) next to its human ``message``. Frontends pick labels,
grouping and help from the code, never by matching message text, so a
message can be reworded freely and a new check needs only a new code here
plus a label in the frontend's table. Codes are part of the contract: rename
one only with a migration of every consumer.
"""

from typing import Dict

#: code -> what it means (for authors, tools and AI helpers; not UI wording).
ISSUE_CODES: Dict[str, str] = {
    # Workflow shape
    "no_start_node": "The workflow has no Start node.",
    "multiple_start_nodes": "The workflow has more than one Start node.",
    "unknown_node_type": "A node's type is not registered.",
    "deleted_node_stub": "A deleted-node record (tombstone) is still in the workflow.",
    "missing_node": "A connection or input source names a node that does not exist.",
    "unreachable": "A node cannot be reached from the Start node.",
    "merge_beacon_unconnected": "A branch ends in a Merge Beacon that feeds no Merge.",
    # Ports and connections
    "undeclared_port": "A connection uses a port the node type does not have.",
    "hidden_output_connection": "A connection leaves an output this node's settings never use.",
    "hidden_input_connection": "A connection enters an input this node's settings never read.",
    "duplicate_input_source": "One node reads the same upstream payload or Vault key twice.",
    "type_mismatch": "An active Upstream connection carries a type the input does not take.",
    # Vault
    "undeclared_vault_key": "A required Vault read names a key no node writes.",
    "unwritten_vault_key": "An optional Vault read names a key no node writes (fallback used).",
    "vault_source_key_missing": "An input set to read from the Vault has no key.",
    "vault_output_key_missing": "Vault output is on but has no key.",
    "vault_type_mismatch": "A Vault key's written type differs from the reader's type.",
    "ai_session_tag_missing": "A key read as an AI session is not written as one.",
    "vault_race": "Every writer of a Vault key is on a parallel branch to its reader.",
    "chat_session_key_missing": "Chat session is on but has no session key.",
    # Files, secrets, platform
    "missing_file_path": "A required file path is empty.",
    "invalid_file_path": "A file path cannot be interpreted.",
    "invalid_number": "A number field is not a finite number inside its allowed range.",
    "file_not_found": "A file to read does not exist at validation time.",
    "secret_not_configured": "A required secret field names no key.",
    "secret_missing": "The named secret is not in the secrets store.",
    "window_placement_unsupported": "Window placement is not available on this platform.",
    "window_close_unsupported": "Closing the window at run end is not available here.",
    # Error Mux
    "mux_route_problem": "An Error Mux route is malformed.",
    "mux_no_codes": "An Error Mux lists no error codes.",
    "mux_no_input": "An Error Mux has no incoming connection.",
    "mux_wrong_source_port": "An Error Mux is fed from a port other than 'error'.",
    "mux_unknown_code": "An Error Mux route lists a code its upstream never raises.",
    "mux_route_unconnected": "An Error Mux route lists codes but goes nowhere.",
    "mux_unmatched_unconnected": "The Error Mux unmatched route is on but goes nowhere.",
}
