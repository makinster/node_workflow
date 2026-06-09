"""Random branch node — routes to path_a or path_b at random."""

import random
from typing import Any, ClassVar, Dict, List, Optional

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


class RandomBranchNode(Node):
    """Randomly selects one of two output ports using _route_via_port."""

    node_type: ClassVar[str] = "random_branch_node"
    display_name: ClassVar[str] = "Random Branch"
    description: ClassVar[str] = "Routes to path_a or path_b at random"
    category: ClassVar[str] = NodeCategory.DEBUG
    input_ports: ClassVar[List[str]] = ["input"]
    output_ports: ClassVar[List[str]] = ["path_a", "path_b"]
    default_config: ClassVar[Dict[str, Any]] = {"seed": ""}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "seed": {"type": "string", "label": "Random Seed (empty = random)", "required": False},
    }

    async def execute(self, context: NodeContext) -> None:
        seed_raw = self.config.get("seed", "")
        rng = random.Random(seed_raw if seed_raw != "" else None)
        port = rng.choice(["path_a", "path_b"])
        value = context.inputs.get("input", "")
        context.signal_done({"data": {"_route_via_port": port, port: value}})
