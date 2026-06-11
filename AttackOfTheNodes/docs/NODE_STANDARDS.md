# Node Standards

Standards for node output routing, vault interaction, and resource handle
patterns. Read alongside `AGENT_START_GUIDE.md` when adding or changing nodes.

## Standard Output Routing Model

Every node signals completion through `context.signal_done(payload)`. The
payload carries output under port names:

```python
await context.signal_done({"data": {"default": value}})
```

Multi-output and branching nodes use named port keys (`path_a`, `path_b`,
etc.). The `Supervisor` writes these to the transient `MemoryBank` store so
downstream nodes receive them as prepared inputs.

Durable output for user-facing results goes through `context.memory_bank`
membank writes. Named vault keys declared in `membank_outputs` are visible to
all branches and readable via the Vault in node config.

## Typed Vault Outputs

Vault writes can carry an explicit `type` field alongside the value. Types:
`string`, `number`, `boolean`, `file`, `ai_session`.

`string`, `number`, and `boolean` entries behave as before — pure JSON values
stored and read by name.

`file` and `ai_session` entries store a type tag and a string reference key.
The actual Python handle lives in `RunSession`, registered by the node that
opens or creates it:

```python
context.run_session.register_resource(ref_key, handle)
# write the reference to the vault
context.memory_bank.set(vault_key, {"type": "file", "ref_key": ref_key})
```

A downstream node that reads a `file` or `ai_session` vault entry retrieves
the handle through:

```python
handle = context.run_session.get_resource(ref_key)
```

The type tag tells the node and the framework which lookup path to use. From
the user's perspective this is invisible — they see `filename (file)` in the
Vault source dropdown.

Input source dropdowns type-filter automatically. An input declared as
accepting `file` shows only `file` vault entries; an LLM continuation input
shows only `ai_session` entries.

## AI Session Config-Driven Output (LLM Nodes)

There is no separate Chat Session Node. Any LLM node can opt into session
persistence via a config checkbox ("keep active AI session") and a
user-supplied session key.

When the checkbox is set and the node executes:

1. The node opens or retrieves a session handle (provider client + message
   history list) from `RunSession` under the session key.
2. It appends the current turn and runs inference.
3. It registers the updated session handle back in `RunSession`.
4. It writes `{"type": "ai_session", "ref_key": <session_key>}` to the vault
   under the session key.

The first LLM node with a given session key starts the session. All subsequent
nodes that select the same vault key from their source dropdown continue it.
Message history lives in the session object in `RunSession`; `MemoryBank`
holds only the type tag and reference key.

Downstream LLM nodes that want to continue a session:
- Select the vault source for their chat input.
- See `chat_name (ai_session)` in the type-filtered dropdown.
- Retrieve the session via `context.run_session.get_resource(session_key)`,
  append their turn, and re-register the handle.

## Validator Rules for Typed Vault References

Two tiers apply to vault entries that reference RunSession handles:

- **Error**: no node in the workflow declares the vault key at all. The key
  can never exist at runtime regardless of timing. This blocks the workflow.
- **Warning**: a node declares the key but lives on a parallel branch where
  execution order cannot be guaranteed. The validator recommends inserting a
  Wait Until node or restructuring branches so the key is written before it is
  read.

The validator must not attempt to infer runtime timing from node count, type,
or branch depth. Static analysis cannot determine which branch is slower.
Warning plus Wait Until suggestion is the correct ceiling.

This error/warning split applies uniformly to string, number, file, and
ai_session vault references.
