"""Compatibility projection of the node metadata registry's execution contracts.

The authored records live in ``backend/node_metadata.py`` (record v1); this
module keeps the old import working and is never edited by hand. Contracts
describe runtime values beyond the port's broad data type; they never drive
execution or validation.
"""

from .node_metadata import execution_contracts

EXECUTION_CONTRACTS = execution_contracts()
