"""Frontend constants for structural node type identifiers.

These values are persisted workflow node ``type`` strings. Keep the strings
stable; the constants exist only to avoid scattering UI/editor checks.
"""

START_NODE_TYPE = "start_node"
END_NODE_TYPE = "end_node"
BRANCH_NODE_TYPE = "branch_node"
BRANCH_END_NODE_TYPE = "branch_end_node"
MERGE_NODE_TYPE = "merge_node"
TEXT_OUTPUT_NODE_TYPE = "text_output_node"
TOMBSTONE_NODE_TYPE = "tombstone_node"
WAIT_UNTIL_NODE_TYPE = "wait_until_node"

