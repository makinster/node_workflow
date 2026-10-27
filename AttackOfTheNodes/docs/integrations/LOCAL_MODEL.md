# Ask local model

Owner-approved decisions 1–10, 2026-10-26. One text question plus optional
Context, one final text answer. Native Ollama API; no tools, history, attachments,
vision, CLI process, retries, model pulls or cloud fallback.

## Configure once

Options → General: **Local model server URL** defaults to
`http://localhost:11434`. **Local default model** is a per-machine installed
model name. No particular model is shipped. Both model fields list installed
names using a read-only `GET /api/tags` with a two-second deadline. The Options
picker fills an empty draft if exactly one model is installed; Save commits it,
Cancel leaves settings unchanged. Multiple/zero models do not select one.
A node's Model override starts with **Options default (<current default>)**;
that choice saves an empty override. The remaining choices are installed names.
If listing fails, both controls show **Couldn't list models** and accept typed
text. Previously saved names absent from the list remain labelled, preserving
workflows for repair. Editing the Options URL refreshes its picker; discovery
never generates, loads or pulls a model.
[Model-list API](https://docs.ollama.com/api/tags).
The URL never comes from the workflow. HTTP(S) base URLs only: no credentials,
path, query or fragment. Environment proxies and redirects are disabled.

The node reads `/api/tags` and `/api/show` before one `/api/chat` call. It
requires local GGUF metadata, completion capability and compatible thinking
controls; cloud names/remote indirection fail. It never installs or changes a
server. A trusted Options endpoint remains a trust boundary: local transport
alone is not a privacy audit. No sign-in is needed for the normal local API.
[Ollama authentication](https://docs.ollama.com/api/authentication),
[Show metadata](https://docs.ollama.com/api-reference/show-model-details).

## Inputs and controls

- Question [string], required: Upstream payload / Vault / Configured.
- Context [string], optional: the same sources plus Not used (default off state).
- Context is appended as labelled data after the question. Context ≤8,000
  characters; assembled question ≤20,000, valid UTF-8, no silent AOTN trimming.
- Reply as JSON defaults off. On sends `format:"json"` plus a JSON instruction;
  validates JSON syntax and returns the original text. Check reply owns expected
  fields/types. JSON alone proves neither shape nor factual correctness.
- Thinking defaults off, sent explicitly. Supported boolean control is checked
  against show metadata; unsupported controls fail. No thinking text is saved
  or published. Non-thinking models may use off without thinking metadata.
- Stop after defaults to 180 seconds, range 10–600, including metadata, queue,
  load and generation; connect deadline ≤5 seconds within that total. Timeout
  stops waiting; it does not prove server computation stopped.
- Context window 8,192 (512–262,144), Temperature 0.2 (0–2), Max output tokens
  2,048 (1–8,192) stay visible **per node below the main controls**. A known
  model context ceiling is checked before inference. Character caps do not
  guarantee token fit; the server may truncate a long prompt. Measure with
  realistic small Context Packs before relying on large inputs.
- Always `stream:false`, `keep_alive:"5m"`. No preload or unload side effects.
  One total deadline covers the whole visit. No automatic retry, including
  failed/over-budget requests.

The declared sources, runtime accepted sources and actual Source menu values
are tested together. Standard availability filtering still removes unconnected,
incompatible or duplicate choices; Not used is a disabled optional input, not
another source. Typed Vault discovery includes eligible upstream secondary
outputs and excludes incompatible/self/downstream-only writers. No new
node-specific source screen was needed. The model setting uses a shared picker.
The [all-node audit](../audits/source_menus_2026_10_26/README.md) covers
secondary/dynamic writes, multi-writer keys and fan-in availability.

[Chat protocol](https://docs.ollama.com/api/chat),
[JSON format](https://docs.ollama.com/capabilities/structured-outputs),
[Thinking](https://docs.ollama.com/capabilities/thinking).

## Outputs and failures

Answer [string] goes downstream by default, optionally also to a Vault key.
The standard Forward incoming payload unchanged checkbox forwards the Question
input port's original object; an enabled Answer Vault output still holds the
computed answer. This follows Ask Hermes' designated primary-input behaviour.

Run details [var] is Vault-only and off by default. It holds resolved model,
optional digest, input/output/cached token counts, wall seconds, server total,
load, input and output seconds, and completion mode. Missing/invalid optional
metrics are null, never invented zero/cost. No question, Context, duplicate
answer or thinking trace is stored in details. Answer and Run details keys
must be distinct. [Metrics](https://docs.ollama.com/api/usage).

Every response envelope is capped at 1 MiB, including metadata/thinking;
Answer at 16,000 characters. Require a complete assistant answer with stop
reason `stop`; reject blank, tool-call, token-limit and incomplete replies.
JSON mode rejects malformed JSON/non-finite constants/duplicate keys. Error
messages are fixed and exclude provider bodies, request text and URLs.

Codes: `settings_invalid`, `invalid_config`, `server_unreachable`, `model_missing`,
`local_model_required`, `server_busy`, `timed_out`, `server_error`,
`response_too_large`, `incomplete_reply`, `invalid_response`,
`thinking_unsupported`, `text_too_long`, `context_too_long`.
All are nonretryable automatically; normal error paths/recovery remain available.
No blank-success answer, auto-start, auto-pull or hosted fallback.

## Build, inspect and check

[Example spec](../../examples/ask_local_model.json):
Context Pack → Ask local model (JSON) → Check reply → Notify me.
Use `aotn describe ask_local_model_node` and
`aotn build examples/ask_local_model.json --check` before an approved run.
A build check does not contact Ollama or confirm that Options point at a
running/loaded model. Do not run the notification example as an unapproved test.

Helper: `aotn_node_helper/specs/ask_local_model_node.json`; create_node generated
registration/class/tests. The maintained class adds Context's Not used state
and execution, as in Ask Hermes; preserve those when regenerating. The generated
producer smoke now asserts missing Question fails before network, rather than
pretending a default producer succeeds.

[Built screens](../audits/local_model_2026_10_26/README.md),
[measured delivery case](../delivery_tests/ask-local-model.json).
Only the two owner-approved smoke requests used real inference; automated tests
use a local fake. No live workflow, schedule, Options file or service was changed.
