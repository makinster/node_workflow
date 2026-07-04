"""Chat Completion node — real LLM execution via backend.llm_provider."""

import asyncio
from typing import Any, ClassVar, Dict, List, Optional

from ..llm_provider import DEFAULT_MODEL_ID, get_client, supported_model_ids
from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


class ChatCompletionNode(Node):
    """Send a prompt (and optional document) to an LLM and route the response.

    Follows the NODE_STANDARDS Basic LLM Node pattern: standard input sources
    for prompt/document, dead-drop passthrough default with a locked-on vault
    write, and config-driven AI session persistence ("Keep active AI session")
    backed by RunSession chat history plus an ai_session-typed vault entry.
    """

    node_type: ClassVar[str] = "chat_completion_node"
    display_name: ClassVar[str] = "Chat Completion"
    description: ClassVar[str] = "Send a prompt to an LLM and receive a text response"
    category: ClassVar[str] = NodeCategory.AI
    input_ports: ClassVar[List[str]] = ["prompt", "document"]
    output_ports: ClassVar[List[str]] = ["default"]
    input_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {
        "prompt": {
            "name": "Prompt",
            "description": "Instruction text sent to the model",
            "data_type": "string",
            "required": True,
            "sources": ["upstream", "vault", "configured"],
        },
        "document": {
            "name": "Document / Context",
            "description": "Optional document appended to the prompt",
            "data_type": "string",
            "required": False,
            "sources": ["upstream", "vault"],
        },
    }
    output_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {
        "default": {
            "name": "LLM Result",
            "description": "Model response text (or forwarded payload on dead-drop)",
            "data_type": "string",
            "required": True,
            "to": ["downstream", "vault"],
            "pass_through": True,
        },
    }
    default_config: ClassVar[Dict[str, Any]] = {
        "prompt_source": "Configured",
        "prompt_vault_key": "",
        "prompt": "",
        "document_source": "Upstream payload",
        "document_vault_key": "",
        "continue_session_key": "",
        "model": DEFAULT_MODEL_ID,
        "max_tokens": 1024,
        "temperature": 1.0,
        "api_key_secret": "",
        "use_chat_session": False,
        "session_key": "",
        "transient_output": False,
        "dead_drop_passthrough": True,
        "vault_write": True,
        "vault_write_key": "",
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "prompt_source": {
            "type": "select",
            "label": "Prompt source",
            "options": ["Upstream payload", "Vault", "Configured"],
            "tab": "Source",
            "description": "Where the prompt comes from at execution time",
        },
        "prompt_vault_key": {
            "type": "string",
            "label": "Prompt Vault key",
            "required": False,
            "tab": "Source",
            "enabled_when": {"prompt_source": "Vault"},
        },
        "document_source": {
            "type": "select",
            "label": "Document / context source",
            "options": ["Upstream payload", "Vault"],
            "tab": "Source",
            "description": "Optional document appended to the prompt",
        },
        "document_vault_key": {
            "type": "string",
            "label": "Document Vault key",
            "required": False,
            "tab": "Source",
            "enabled_when": {"document_source": "Vault"},
        },
        "continue_session_key": {
            "type": "string",
            "label": "Continue AI session (ai_session Vault key)",
            "required": False,
            "tab": "Source",
            "vault_type": "ai_session",
            "description": "Vault key of an ai_session entry whose history this call continues",
        },
        "prompt": {
            "type": "multiline",
            "label": "Prompt",
            "required": False,
            "tab": "Parameters",
            "enabled_when": {"prompt_source": "Configured"},
        },
        "model": {
            "type": "select",
            "label": "Model",
            "options": supported_model_ids(),
            "required": True,
            "tab": "Parameters",
        },
        "max_tokens": {
            "type": "integer",
            "label": "Max tokens",
            "required": True,
            "tab": "Parameters",
        },
        "temperature": {
            "type": "float",
            "label": "Temperature",
            "required": True,
            "tab": "Parameters",
            "description": "Ignored by models that do not accept sampling parameters",
        },
        "api_key_secret": {
            "type": "string",
            "label": "API key (secrets store key)",
            "secret": True,
            "required": True,
            "tab": "Parameters",
        },
        "use_chat_session": {
            "type": "boolean",
            "label": "Keep active AI session",
            "tab": "Parameters",
        },
        "session_key": {
            "type": "string",
            "label": "Session key",
            "required": False,
            "tab": "Parameters",
            "enabled_when": {"use_chat_session": True},
        },
        "transient_output": {
            "type": "boolean",
            "label": "Send LLM result to next node",
            "tab": "Payloads",
            "mutually_exclusive_with": ["dead_drop_passthrough"],
        },
        "dead_drop_passthrough": {
            "type": "boolean",
            "label": "Forward incoming payload unchanged",
            "tab": "Payloads",
            "mutually_exclusive_with": ["transient_output"],
        },
        "vault_write": {
            "type": "boolean",
            "label": "Save LLM result to Vault",
            "tab": "Payloads",
            "enabled_when": {"transient_output": True},
        },
        "vault_write_key": {
            "type": "string",
            "label": "Result Vault key",
            "required": False,
            "tab": "Payloads",
            "enabled_when": {"vault_write": True},
        },
    }

    async def execute(self, context: NodeContext) -> None:
        prompt = self._resolve_prompt(context)
        if prompt is None or not prompt.strip():
            context.signal_error(RuntimeError("Prompt is empty — configure a prompt source"))
            return
        document = self._resolve_document(context)

        secret_key = str(self.config.get("api_key_secret") or "").strip()
        if not secret_key:
            context.signal_error(RuntimeError("No API key secret configured"))
            return
        api_key = context.get_secret(secret_key)
        if not api_key:
            context.signal_error(
                RuntimeError(f"API key secret '{secret_key}' not found in secrets store")
            )
            return

        history = self._resolve_history(context)
        user_content = prompt if document is None else f"{prompt}\n\n{document}"
        messages = history + [{"role": "user", "content": user_content}]

        client = get_client("anthropic")
        try:
            result = await asyncio.to_thread(
                client.complete,
                model=str(self.config.get("model") or DEFAULT_MODEL_ID),
                messages=messages,
                max_tokens=int(self.config.get("max_tokens") or 1024),
                temperature=float(self.config.get("temperature") or 1.0),
                api_key=api_key,
            )
        except Exception as exc:  # network layer may raise; fail the node cleanly
            context.signal_error(RuntimeError(f"Chat completion failed: {exc}"))
            return

        if not result.ok:
            # No session mutation and no vault result on failure.
            context.signal_error(RuntimeError(f"Chat completion failed: {result.error}"))
            return

        self._persist_session(context, history, user_content, result.text)

        if self.config.get("vault_write", True):
            vault_key = str(self.config.get("vault_write_key") or "").strip()
            if vault_key:
                context.memory_bank.store_persistent(vault_key, result.text)

        if self.config.get("transient_output"):
            payload: Any = result.text
        else:
            # Dead-drop passthrough: forward the incoming transient payload.
            payload = context.inputs.get("document")
            if payload is None:
                payload = context.inputs.get("prompt")
        context.signal_done({"data": {"default": payload}})

    def _resolve_prompt(self, context: NodeContext) -> Optional[str]:
        source = self.config.get("prompt_source", "Configured")
        if source == "Upstream payload":
            value = context.inputs.get("prompt")
        elif source == "Vault":
            key = str(self.config.get("prompt_vault_key") or "").strip()
            value = context.memory_bank.read_persistent(key) if key else None
        else:
            value = self.config.get("prompt")
        return None if value is None else str(value)

    def _resolve_document(self, context: NodeContext) -> Optional[str]:
        source = self.config.get("document_source", "Upstream payload")
        if source == "Vault":
            key = str(self.config.get("document_vault_key") or "").strip()
            value = context.memory_bank.read_persistent(key) if key else None
        else:
            value = context.inputs.get("document")
        return None if value is None else str(value)

    def _resolve_history(self, context: NodeContext) -> List[Dict[str, str]]:
        """Prior turns for this call: continuation input wins over own session."""
        if context.run_session is None:
            return []
        continue_key = str(self.config.get("continue_session_key") or "").strip()
        if continue_key:
            entry = context.memory_bank.read_persistent(continue_key)
            ref_key = continue_key
            if isinstance(entry, dict) and entry.get("type") == "ai_session":
                ref_key = str(entry.get("ref_key") or continue_key)
            return context.run_session.get_chat_history(ref_key)
        if self.config.get("use_chat_session"):
            session_key = str(self.config.get("session_key") or "").strip()
            if session_key:
                return context.run_session.get_chat_history(session_key)
        return []

    def _persist_session(
        self,
        context: NodeContext,
        history: List[Dict[str, str]],
        user_content: str,
        response_text: str,
    ) -> None:
        """Extend the named session after a successful call (checkbox-gated).

        History lives in RunSession; the vault holds only the ai_session type
        tag and reference key (NODE_STANDARDS, Typed Vault Outputs).
        """
        if not self.config.get("use_chat_session") or context.run_session is None:
            return
        session_key = str(self.config.get("session_key") or "").strip()
        if not session_key:
            return
        session_history = context.run_session.get_or_create_chat_session(session_key)
        if not session_history and history:
            # Continuing another session into a fresh key: seed the prior turns.
            session_history.extend(history)
        context.run_session.append_chat_message(session_key, "user", user_content)
        context.run_session.append_chat_message(session_key, "assistant", response_text)
        context.memory_bank.store_persistent(
            session_key,
            {"type": "ai_session", "ref_key": session_key},
            type_tag="ai_session",
        )
