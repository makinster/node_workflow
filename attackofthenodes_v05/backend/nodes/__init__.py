"""Registered node classes for AttackOfTheNodes v0.5."""

from .branch_node import BranchNode
from .chat_completion_node import ChatCompletionNode
from .concat_node import ConcatNode
from .conditional_node import ConditionalNode
from .embedding_node import EmbeddingNode
from .end_node import EndNode
from .file_reader_node import FileReaderNode
from .get_variable_node import GetVariableNode
from .image_generation_node import ImageGenerationNode
from .set_variable_node import SetVariableNode
from .start_node import StartNode
from .text_output_node import TextOutputNode
from .user_text_input_node import UserTextInputNode
from .wait_until_node import WaitUntilNode

# ── Debug nodes ───────────────────────────────────────────────────────────────
from .debug.counter_node import CounterNode
from .debug.tombstone_node import TombstoneNode
from .debug.deep_branch_node import DeepBranchNode
from .debug.echo_node import EchoNode
from .debug.error_node import ErrorNode
from .debug.logger_node import LoggerNode
from .debug.memory_snapshot_node import MemorySnapshotNode
from .debug.no_op_node import NoOpNode
from .debug.probe_node import ProbeNode
from .debug.random_branch_node import RandomBranchNode
from .debug.repeat_node import RepeatCounterNode
from .debug.sleep_node import SleepNode
from .debug.variable_reader_node import VariableReaderNode
from .debug.variable_setter_node import VariableSetterNode


ALL_NODE_CLASSES = [
    # Flow
    StartNode,
    EndNode,
    BranchNode,
    ConditionalNode,
    WaitUntilNode,
    # Data
    SetVariableNode,
    GetVariableNode,
    ConcatNode,
    VariableSetterNode,
    VariableReaderNode,
    # IO
    TextOutputNode,
    UserTextInputNode,
    FileReaderNode,
    # AI
    ChatCompletionNode,
    ImageGenerationNode,
    EmbeddingNode,
    # Debug
    TombstoneNode,
    EchoNode,
    LoggerNode,
    SleepNode,
    CounterNode,
    MemorySnapshotNode,
    ProbeNode,
    ErrorNode,
    RandomBranchNode,
    DeepBranchNode,
    NoOpNode,
    RepeatCounterNode,
]
