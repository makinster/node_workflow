"""Registered node classes for AttackOfTheNodes v0.5."""

from .branch_node import BranchNode
from .end_node import EndNode
from .start_node import StartNode
from .text_output_node import TextOutputNode


ALL_NODE_CLASSES = [
    StartNode,
    TextOutputNode,
    BranchNode,
    EndNode,
]
