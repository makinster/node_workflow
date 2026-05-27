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


ALL_NODE_CLASSES = [
    StartNode,
    TextOutputNode,
    BranchNode,
    ConditionalNode,
    ChatCompletionNode,
    ImageGenerationNode,
    EmbeddingNode,
    SetVariableNode,
    GetVariableNode,
    ConcatNode,
    UserTextInputNode,
    FileReaderNode,
    EndNode,
]
