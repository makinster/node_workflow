# Approved planning snapshot — 2026-10-26

The owner approved decisions 1–12 and samples in the build request. The copied
planning text below is historical; its pending/no-build wording is superseded.
Build overrides: Debug group/section excluded by default, Include debug nodes
opt-in; Compact cap measured with 25% headroom; entry_kind/port shape reserves
later Bundle compatibility; repeated_shapes added to the delivery case. The
[built contract](../../integrations/META_NODES.md) owns the final behavior.

---

# Meta nodes · request (step 0)

2026-10-26 · `meta-nodes` · owner label: **meta nodes**.
Base `3f36552`, own branch `codex/meta-nodes-samples`.

Make the node contracts available to an AI step, then check its drafted
`aotn-workflow/1` spec before it can reach owner approval or a future builder.
Example: “Tell me Ready” → a small notification draft → valid parsed spec,
or a readable list such as `show · config.misspelled_config · Unknown key`.

- Node catalogue: all or group/tag/search-filtered contracts; compact/detailed;
  Text or JSON; an explicit size cap.
- Check workflow spec: JSON text from Upstream / Vault / Configured → parsed
  record on success; problems on the existing error path on failure.
- Neither saves, runs, activates or edits a workflow. No outside API or account.
- Target: the owner's 80×24 WSL terminal and future AI steps.
- Success: useful bounded contracts, honest errors, and no library writes.

Only steps 0–4 are requested. [Decisions](approved-decisions.md) and samples are
**proposals awaiting owner approval**. [Machine form](workflow-request.json).
