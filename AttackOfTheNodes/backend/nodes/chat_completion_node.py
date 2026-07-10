"""Chat Completion node — real LLM execution via backend.llm_provider."""

import asyncio
from typing import Any, ClassVar, Dict, List, Optional

from ..llm_provider import DEFAULT_MODEL_ID, get_client, supported_model_ids
from ..node_base import Node, NodeContext
from ..node_category import NodeCategory


# Prompt-source mode that resumes a declared AI session instead of sending a
# fresh prompt. The validator recognizes this label when deriving vault reads
# (backend/validator.py) — keep the two in sync.
CONTINUE_SESSION_SOURCE = "Continue AI session"


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
        "document": "",
        "continue_session_key": "",
        "model": DEFAULT_MODEL_ID,
        "max_tokens": 1024,
        "temperature": 1.0,
        "api_key_secret": "",
        "use_chat_session": False,
        "session_key": "",
        # Output routing: the Result is the designated downstream payload
        # (dead-drop off by default), also duplicated to the Vault by default.
        "transient_output": True,
        "dead_drop_passthrough": False,
        "vault_write": True,
        "vault_write_key": "",
        "vault_write_description": "",
        "transient_outputs": [],
    }
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {
        "prompt_source": {
            "type": "select",
            "label": "Prompt source",
            "options": [
                "Upstream payload",
                "Vault",
                "Configured",
                CONTINUE_SESSION_SOURCE,
            ],
            "tab": "Source",
            "section": "Required Inputs",
            "description": "Where the prompt comes from at execution time",
        },
        "prompt_vault_key": {
            "type": "string",
            "label": "Prompt Vault key",
            "required": False,
            "tab": "Source",
            "section": "Required Inputs",
            "vault_type": "string",
            "visible_when": {"prompt_source": "Vault"},
        },
        "continue_session_key": {
            "type": "string",
            "label": "Session",
            "required": False,
            "tab": "Source",
            "section": "Required Inputs",
            "vault_type": "ai_session",
            "visible_when": {"prompt_source": CONTINUE_SESSION_SOURCE},
            "description": "Declared AI session whose chat this node resumes",
        },
        # In Continue mode the document carries the new turn's text, so it is
        # required and its section retitles to "Required Inputs" — but the user
        # still picks the source (Upstream / Vault / Configured).
        "document_source": {
            "type": "select",
            "label": "Document / context source",
            "options": ["Upstream payload", "Vault", "Configured"],
            "tab": "Source",
            "section": "Optional Inputs",
            "description": "Optional document appended to the prompt",
            "required_when": {"prompt_source": CONTINUE_SESSION_SOURCE},
            "section_when": {
                "Required Inputs": {"prompt_source": CONTINUE_SESSION_SOURCE}
            },
        },
        "document_vault_key": {
            "type": "string",
            "label": "Document Vault key",
            "required": False,
            "tab": "Source",
            "section": "Optional Inputs",
            "vault_type": "string",
            "visible_when": {"document_source": "Vault"},
        },
        "prompt": {
            "type": "multiline",
            "label": "Prompt (E to edit, ESC to finish)",
            "required": False,
            "tab": "Parameters",
            "visible_when": {"prompt_source": "Configured"},
        },
        "document": {
            "type": "multiline",
            "label": "Document (E to edit, ESC to finish)",
            "required": False,
            "tab": "Parameters",
            "visible_when": {"document_source": "Configured"},
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
        # The Payloads routing/vault controls are composed by NodeConfigScreen
        # from output_port_metadata (one Downstream node payload + optional
        # Vault payloads), not from schema fields — see the redesigned output
        # model in NODE_STANDARDS.md. The config keys they read/write
        # (dead_drop_passthrough, transient_output, vault_write,
        # vault_write_key, vault_write_description, transient_outputs) live in
        # default_config below.
        "use_chat_session": {
            "type": "boolean",
            "label": "Keep active AI session",
            "tab": "Payloads",
            "section": "AI Session",
            "visible_when": {
                "prompt_source": ["Upstream payload", "Vault", "Configured"],
            },
            "description": (
                "When continuing a session, extends that same session — "
                "no new key needed"
            ),
        },
        # When continuing, the resumed session is the one kept active, so no
        # new key is asked for: the field is hidden unless a non-continue
        # prompt source is selected.
        "session_key": {
            "type": "string",
            "label": "Session key",
            "required": False,
            "tab": "Payloads",
            "section": "AI Session",
            "visible_when": {
                "use_chat_session": True,
                "prompt_source": ["Upstream payload", "Vault", "Configured"],
            },
        },
    }

    async def execute(self, context: NodeContext) -> None:
        continuing = self.config.get("prompt_source") == CONTINUE_SESSION_SOURCE
        document = self._resolve_document(context)

        if continuing:
            prompt = None
        else:
            prompt = self._resolve_prompt(context)
            if prompt is None or not prompt.strip():
                context.signal_error(
                    RuntimeError("Prompt is empty — configure a prompt source")
                )
                return

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

        onward_key = ""
        if continuing:
            ref = self._continuation_ref(context)
            if not ref:
                context.signal_error(
                    RuntimeError("Select an AI session to continue")
                )
                return
            if context.run_session is None:
                context.signal_error(
                    RuntimeError("AI sessions are unavailable outside a run")
                )
                return
            history = context.run_session.get_chat_history(ref)
            if not history:
                context.signal_error(
                    RuntimeError(f"AI session '{ref}' has no history to continue")
                )
                return
            # The resumed session replaces the prompt; the Document input
            # carries the new turn's text and is required in this mode.
            if document is None or not document.strip():
                context.signal_error(
                    RuntimeError(
                        "Continue AI session needs Document text to send "
                        "alongside the resumed chat"
                    )
                )
                return
            user_content: Optional[str] = document
            messages = history + [{"role": "user", "content": user_content}]
            # Continuing a session extends the resumed session itself — no
            # separate output key or Payloads-tab checkbox is needed.
            onward_key = ref
        else:
            history = self._resolve_history(context)
            user_content = prompt if document is None else f"{prompt}\n\n{document}"
            messages = history + [{"role": "user", "content": user_content}]
            if self.config.get("use_chat_session"):
                onward_key = str(self.config.get("session_key") or "").strip()

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

        self._persist_session(context, onward_key, history, user_content, result.text)

        if self.config.get("vault_write", True):
            vault_key = str(self.config.get("vault_write_key") or "").strip()
            if vault_key:
                context.memory_bank.store_persistent(vault_key, result.text)

        if self.config.get("dead_drop_passthrough"):
            # Forward the incoming transient payload unchanged.
            payload: Any = context.inputs.get("document")
            if payload is None:
                payload = context.inputs.get("prompt")
        else:
            # The Result is the designated downstream payload.
            payload = result.text
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
        elif source == "Configured":
            value = self.config.get("document")
        else:
            value = context.inputs.get("document")
        return None if value is None else str(value)

    def _resolve_history(self, context: NodeContext) -> List[Dict[str, str]]:
        """Prior turns of this node's own session (checkbox-gated)."""
        if context.run_session is None:
            return []
        if self.config.get("use_chat_session"):
            session_key = str(self.config.get("session_key") or "").strip()
            if session_key:
                return context.run_session.get_chat_history(session_key)
        return []

    def _continuation_ref(self, context: NodeContext) -> str:
        """Resolve the continued session's RunSession key from the vault entry."""
        key = str(self.config.get("continue_session_key") or "").strip()
        if not key:
            return ""
        entry = context.memory_bank.read_persistent(key)
        if isinstance(entry, dict) and entry.get("type") == "ai_session":
            return str(entry.get("ref_key") or key)
        return key

    def _persist_session(
        self,
        context: NodeContext,
        onward_key: str,
        history: List[Dict[str, str]],
        user_content: Optional[str],
        response_text: str,
    ) -> None:
        """Extend the kept-active session after a successful call.

        ``onward_key`` is the session to extend: this node's own session key in
        normal mode, or the resumed session's ref when continuing (so keeping
        the session active extends the same chat rather than forking a copy).
        History lives in RunSession; the vault holds only the ai_session type
        tag and reference key (NODE_STANDARDS, Typed Vault Outputs).
        """
        if not onward_key or context.run_session is None:
            return
        session_history = context.run_session.get_or_create_chat_session(onward_key)
        if not session_history and history:
            # Seeding a fresh key from another session's prior turns.
            session_history.extend(history)
        if user_content is not None:
            context.run_session.append_chat_message(onward_key, "user", user_content)
        context.run_session.append_chat_message(onward_key, "assistant", response_text)
        context.memory_bank.store_persistent(
            onward_key,
            {"type": "ai_session", "ref_key": onward_key},
            type_tag="ai_session",
        )
