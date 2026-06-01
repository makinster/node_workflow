"""Node category enum for AttackOfTheNodes."""

from enum import Enum


class NodeCategory(str, Enum):
    FLOW = "flow"
    IO = "io"
    DATA = "data"
    AI = "ai"
    DEBUG = "debug"
    UTILITY = "utility"
