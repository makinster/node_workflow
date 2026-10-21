"""The deliberately small C4 tool surface (JSON Schema 2020-12)."""


def object_schema(properties=None, required=()):
    return {"type": "object", "properties": properties or {},
            "required": list(required), "additionalProperties": False}


RUN_SCHEMA = object_schema({
    "run_id": {"type": ["string", "null"]},
    "workflow_id": {"type": ["string", "null"]},
    "workflow_name": {"type": "string"},
    "final_state": {"type": "string"}, "exit_code": {"type": "integer"},
    "outputs": {"type": "array"}, "values": {"type": "object"},
    "errors": {"type": "array"}, "unhandled_error_count": {"type": "integer"},
    "node_timings": {"type": "object"}, "revision": {"type": ["string", "null"]},
}, ("run_id", "final_state", "exit_code", "outputs", "values"))

TOOLS = [
    {"name": "list_workflows", "description": "List saved workflow IDs, names, callable flags and contract inputs/results; includes potential input prompts.",
     "inputSchema": object_schema(),
     "outputSchema": object_schema({"workflows": {"type": "array", "items": {
         "type": "object", "required": ["id", "name", "callable", "inputs", "results", "asks"],
         "properties": {"id": {"type": "string"}, "name": {"type": "string"},
                        "callable": {"type": "boolean"}, "inputs": {"type": "array"},
                        "results": {"type": "array"}, "asks": {"type": "array", "items": {"type": "string"}}}}}}, ("workflows",))},
    {"name": "run_workflow", "description": "Run a saved workflow by name or ID unattended. Inputs are typed JSON values; @stash:name resolves a named Stash entry. Workflows that may prompt are rejected before starting. Workflow effects are real.",
     "inputSchema": object_schema({"name_or_id": {"type": "string", "minLength": 1},
                                   "inputs": {"type": "object", "default": {}}}, ("name_or_id",)),
     "outputSchema": RUN_SCHEMA},
    {"name": "get_run_status", "description": "Read a persisted run summary by run ID. History contains completed/errored runs, not live progress.",
     "inputSchema": object_schema({"run_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,128}$"}}, ("run_id",)),
     "outputSchema": object_schema({"run": {"type": "object"}}, ("run",))},
    {"name": "get_recent_events", "description": "Read the newest persisted run summaries; this is not an events.jsonl stream.",
     "inputSchema": object_schema({"limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10}}),
     "outputSchema": object_schema({"runs": {"type": "array", "items": {"type": "object"}}}, ("runs",))},
]
BY_NAME = {tool["name"]: tool for tool in TOOLS}


def validate_arguments(name, args):
    """Validate exactly this fixed schema subset without a new dependency."""
    import re
    schema = BY_NAME[name]["inputSchema"]
    if not isinstance(args, dict):
        raise ValueError("arguments must be an object")
    if set(args) - set(schema["properties"]):
        raise ValueError("unknown argument(s): " + ", ".join(sorted(set(args) - set(schema["properties"]))))
    for key in schema["required"]:
        if key not in args:
            raise ValueError(f"missing argument: {key}")
    for key, value in args.items():
        rule = schema["properties"][key]
        kind = rule["type"]
        if kind == "object" and not isinstance(value, dict):
            raise ValueError(f"{key} must be an object")
        if kind == "string":
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{key} must be a nonempty string")
            if "pattern" in rule and not re.fullmatch(rule["pattern"], value):
                raise ValueError(f"invalid {key}")
        if kind == "integer" and (type(value) is not int or not rule["minimum"] <= value <= rule["maximum"]):
            raise ValueError(f"{key} must be an integer from {rule['minimum']} to {rule['maximum']}")
