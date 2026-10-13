# Recovery and Editor UX Build Plan (UX1–UX6), then back to Step 4

Status: approved by the owner on 2026-10-13. This plan comes from the
October 13 review of PRs #41–#43. It replaces nothing in
[DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md); it is a detour that
ends by returning to that plan's Step 4.

The review evidence and probe scripts live outside the repo:
`/mnt/c/Users/makin/.codex/visualizations/2026/10/13/01a133cc-ea38-7ea2-9532-cf2abb622a32/review/`
(`AGENT_HANDOFF.md`, `PR_REVIEW.md`, `aotn_review41_probe.py`,
`aotn_review43_probe.py`, `aotn_review43_perf.py`). Run the probes with
`/home/makin/src/node_workflow/.venv/bin/python` from `/tmp`. They use
temporary data folders.

## Starting state (2026-10-13)

- `origin/main` is at `09a1402`, after PR #42.
- PR #43 (Error Mux redesign) is **open** on branch `dist/p4-inline-error-mux`
  at `3038634`. Do not merge it until UX2 is in.
- Untracked files that must be left alone:
  - `.claude/launch.json`;
  - `AttackOfTheNodes/"C:\...\test.txt"`;
  - `AttackOfTheNodes/Workflow started`.

## Owner decisions (binding for this detour)

| # | Decision |
|---|---|
| U1 | Unpicking a caught error whose recovery branch already has nodes opens a confirmation: **Leave unlinked** (keep the nodes and drop the connection), **Delete branch** (remove the branch's nodes), or **Cancel** (re-pick the error). |
| U2 | After a Catch errors insertion, the editor stays on the **normal path**. It does not jump to a recovery branch. |
| U3 | **Ctrl+Space** saves and keeps the node editor open. Inside a multi-line text box it also commits the text and leaves text editing, and Enter stays a newline. **Ctrl+S** saves and closes, as it does today. |
| U4 | The **Show error path** checkbox goes away. The node's Errors section keeps listing all its errors, now in friendly wording. Under that list (pick the better spot: under the header or at the bottom of the scrollable list) is one focusable widget that **spawns or opens an Error Mux** for this node. Choosing which errors to catch stays in the mux editor; passing picks from the originating node into the mux is **postponed**. |
| U5 | Friendly node labels are display-only: the alias plus a short distinguishing suffix only when two nodes share a label. Stored IDs never change, and the raw ID stays available, for example in details or Connections. |
| U6 | Recovery is edited in **one place**, the mux editor. The originating node shows status and an action, not a second set of editable controls. |
| U7 | **Reuse rule:** reuse a mux only when the node's normal output connects directly to that mux's `input`. Otherwise insert a new mux after the node, so its previous downstream continues on **No error**. |
| U8 | **Insert and cancel:** inserting a mux is a real graph edit, after which the mux editor opens. If that first edit of the new mux is cancelled, the mux is removed and the original wiring restored. |
| U9 | **Saving is per node.** Jumping to another node with unsaved changes asks **Save / Discard / Stay**. There is no save-all yet. |
| U10 | Direct `error`-port connections keep working (engine, validator, display of existing wired paths), but the UI no longer promotes them. |

## Process (same as the distributed steps)

Each phase is one PR, or two where noted:

- branch from the latest `main`;
- add real tests, including ones that fail on the old code;
- run the full suite, `compileall` and `git diff --check`;
- do an adversarial self-review;
- update the docs (`SESSION_LOG.md`, the named docs, this plan's status column);
- open the PR, then merge it with a merge commit.

The hard rules from `DISTRIBUTED_EXECUTION_PROMPT.md` still apply. Gates are
listed per phase.

## Phases

| Phase | Contents | Base | Status |
|---|---|---|---|
| UX1 | Merge branch identity and the never-silently-drop backstop | `main` | Not started |
| UX2 | #43 fixes: legacy pass-along, route draft record, no-edit-save invariant; then merge #43 | `dist/p4-inline-error-mux`, merged with main | Not started |
| UX3 | Measured performance: Branch rows, topology scan | `main` | Not started |
| UX4 | Recovery flow: friendly Errors list, spawn/open mux widget, unpick confirmation, insert/cancel | `main` | Not started |
| UX5 | Connections tab with jumps, Ctrl+Space, Save/Discard/Stay | `main` | Not started |
| UX6 | Friendly node labels, then a presentation pass (sample screens first) | `main` | Not started |

### UX1 — Merge branch identity (bug already on `main`)

**Problem (confirmed).** `frontend/screens/node_config.py:_branch_contexts_by_node`
treats every node with more than one output as a branch point
(`len(output_ports) > 1`). The engine only forms branch groups when a node
spawns branches (`MasterState._register_branch_group`, from a node signalling
`branches`). So a node with several outputs inside a Branch path changes the
Merge option identity from `branch_id:path_b` to `node_id:default`. Examples
are HTTP Request or JSON Path (they list `error`), a node with Show error path
on, and an inline Error Mux. A no-edit Merge save then empties
`branches_to_close`, moves carry-forward to `home:…`, and the editor's
reconciliation disconnects the Merge Beacon. Reproduce with
`aotn_review41_probe.py`, and with variants that use
`http_request_node`/`error_mux_node` in place of `no_op_node` and no toggle.

**Change.**

- Add backend `Node.spawns_branches: ClassVar[bool] = False`. Set it to True
  on `BranchNode` and `DeepBranchNode`; check every node that signals
  `"branches"`. Expose it in factory metadata.
- In `_branch_contexts_by_node`, a node starts new branch contexts only when
  its type spawns branches. Other nodes, whatever their output count, pass
  the current context to every connected target.
- **Backstop.** When a Merge config is built for save
  (`_merge_config_values`, the editor's `_sync_merge_branch_end_connections`)
  and a stored `branches_to_close` / `carry_forward_branch_id` value matches
  no current option, keep it unchanged and show a warning. Never drop it
  silently or disconnect its beacon.

**Acceptance.**

- The #41 probe, plus the HTTP Request and inline-mux variants, keeps the
  closure, the carry-forward and the beacon connection after a no-edit save.
- Run a read-only script over every saved workflow under `workflows/`. It
  records the Merge options before and after; any difference must be
  explained in `SESSION_LOG.md`. Never write to `workflows/`.
- Existing Merge, Branch and beacon tests stay green.

### UX2 — Make PR #43 safe, then merge it

Work on `dist/p4-inline-error-mux`. First bring it up to date with `main`
after UX1: merge `main` into the branch and resolve conflicts.

1. **Legacy pass-along (confirmed).** A no-edit save of a mux that has a
   node-wide `forward: failed_input` writes `forward: error` onto its routes
   and `unmatched_forward: error`.
   - Fix it in `backend/config_migrations.py` (`error_mux_forward_v1`). When
     the node-wide `forward` is present, copy it onto every route that lacks
     `forward` and onto `unmatched_forward` when that is absent. Then remove
     the node-wide key and keep it under `_config_migrations` as evidence.
   - Remove the fallback paths in `node_errors._forward` and
     `mux_forward_for` that this makes redundant, so only one rule remains.
2. **Route draft record (confirmed).** Replace `_mux_removed` (an
   append-only list in which the oldest copy wins) with:
   - `routes_by_id`: each route's id, label, forward and original code order;
   - `owner_by_code`: which route each code belongs to.

   Unpicking a code removes it from its route's active codes but keeps the
   ownership. Re-picking puts it back on the same route, keeping the id,
   name and forward. A route whose codes are all unpicked disappears from the
   rows but keeps its record, so re-picking restores its latest edits.
   Grouped legacy routes stay grouped.
3. **No-edit-save invariant.** Add a mounted test that, for every
   registered node type with a representative config, opens
   `NodeConfigScreen`, saves without edits, and compares the resulting
   config and connections with the input. Equality is semantic: keys with a
   default value are allowed only if the backend treats them identically.
   - Remove the noise keys a no-edit save adds today (`show_error_path:
     false`, empty `default_label`, `transient_outputs: []`), or document why
     each one is equivalent.
4. Add the `recovered` status to `EXECUTION_STATUS_CONTRACT.md`, and fix the
   contradictory Skip text there.
5. Reconnect the "Connections" summary on the mux screen so it refreshes
   after picks, or note that UX5 replaces it.

**Acceptance.**

- `aotn_review43_probe.py` shows:
  - LEGACY_SAVED: same effective forward for every branch;
  - GROUPED_RESELECT: `timeout` back on `both` with `failed_input`;
  - REPEATED_RESELECT: label `Revised`.
- The full suite is green, and `check_node` / `check_ui` pass for
  `error_mux_node`.
- Then merge #43.

### UX3 — Measured performance

1. **Branch rows (confirmed).** At 64 branches the screen takes 1.48 s to
   open and 0.42 s to sync, and 95% of that time is whole-screen
   `self.query` calls in `_sync_branch_payload_rows`. The sync also runs on
   every keystroke in `#branch-count`. Fix it by:
   - keeping a dict of row widgets (port to row, label input and select);
   - calling `set_options` only when the options changed (reuse the
     existing helper that skips unchanged options);
   - mounting new rows in one batch;
   - debouncing the count field (about 150 ms).
2. **Topology scan (confirmed, predates the PRs).** `_branch_contexts_by_node`
   copies `seen` on every edge, so each extra fork/rejoin pair doubles the
   time: 4 pairs take 0.0002 s, 8 take 0.0025 s, 12 take 0.043 s. Use one
   visited set keyed by `(node, branch_id, branch_port)` for the whole scan.
   Keep the first `branch_path` label as display text and document that.
3. **Main editor.** Before optimising, profile mounted navigation on a
   representative wide workflow (ask the owner for one, or use the largest
   one under `workflows/`, read-only).

**Acceptance.** Same machine, `frontend/styles.tcss`, 100×40:

| Measurement | Before | Target |
|---|---|---|
| 64-branch open | 1.48 s | under 0.5 s |
| 64-branch sync | 0.42 s | under 0.03 s |
| 12 fork/rejoin pairs | 0.043 s | under 5 ms |

The topology scan must also return identical results to the old function on
every test graph and on the saved workflows. Record the before and after
numbers in `SESSION_LOG.md`.

### UX4 — Recovery flow from the originating node

1. **Errors section** (`node_config._compose_errors_section`):
   - Show the friendly list, reusing `frontend/error_mux_ui`
     (`friendly_error_choice`). Keep the raw code visible but muted, for
     diagnosis.
   - Replace the Show error path checkbox with one focusable widget.
   - The widget is labelled **Catch errors with an Error Mux…** when there is
     none, or **Open Error Mux (catching N errors) ✓** when U7 finds one. It
     also shows the state in text and colour.
   - Existing `show_error_path: true` configs keep displaying their path (U10).
2. **Spawn or open** (U7/U8):
   - The widget closes the node editor and asks the editor screen to insert
     (`_connect_new_node` already wires the mux inline and moves the old
     downstream to No error), or to find the mux.
   - It then opens the mux's config.
   - Track "inserted by this action". If the mux editor returns `None`
     (cancel), remove the mux and restore the original connection.
   - The selection stays on the normal path (U2).
3. **Unpick confirmation** (U1):
   - In the mux Source tab, unpicking the last code of a route whose port
     has a downstream connection opens a modal with three buttons: Leave
     unlinked, Delete branch, Cancel.
   - "Branch" means the nodes reachable only through that port, stopping at
     any node also reachable another way (for example a Merge).
   - The modal lists those nodes.
   - The choice is applied on save: prune the connection, or delete those
     nodes through the existing delete/tombstone machinery so undo still
     works.
   - Cancel re-picks the code.

**Acceptance.**

- Mounted tests cover each of the following:
  - insertion keeps the downstream on No error;
  - cancelling a fresh insertion leaves the graph identical to before;
  - reopening finds the same mux;
  - the three unpick choices work;
  - deleting a branch stops at a Merge.
- The UX1 Merge probe still passes with an inserted mux.

### UX5 — Connections and saving

- **Connections tab:**
  - list incoming and outgoing connections with friendly node labels, port
    display names and what flows: a payload, or "No payload" when the
    source publishes nothing (use "Null" only if that is the actual value);
  - show Vault reads separately;
  - each row is focusable and Enter jumps to that node's editor;
  - refresh the tab after edits that change ports.
- **Saving:**
  - Ctrl+Space saves and stays (U3), with a fallback binding;
  - before choosing the fallback, verify how Ctrl+Space arrives in Windows
    Terminal and in `textual serve` in a browser (often as `ctrl+@`/NUL).
    Document both in `UI_QUICK_REFERENCE.md`;
  - jumping with unsaved changes asks Save / Discard / Stay (U9);
  - dirty detection compares against the opened config, which is why it
    relies on UX2's no-edit invariant.
- **Diagnose "missing connections"** before claiming a fix. Check
  clipping/layout, the stale summary, and graph edges versus Vault
  dependencies.

**Acceptance.**

- Mounted tests cover jump, the dirty prompt, saving and staying, and
  committing a text area with Ctrl+Space.
- Do a manual check in both terminals and record the result.

### UX6 — Labels and presentation

- **Friendly labels** (U5): a frontend helper gives the alias, plus a short
  suffix only when the label repeats, for example `Fetch ·2` or the last 4
  characters of the ID. Use it in cards, Connections, pickers and modals.
  Keep the raw ID in details.
- **Presentation:**
  - compact tab labels (`1) Source  2) Config  3) Payloads  4) Connections`,
    named per node);
  - remove the duplicate top shortcut line;
  - shorter Errors text;
  - smaller Save/Cancel buttons;
  - consistent focus, disabled and enabled styling.
- **Show 2–3 sample screens to the owner first** (the node config, the Error
  Mux and the editor), then roll the approved style out through shared CSS
  and widgets.

**Acceptance.** The owner approves the samples, `check_ui` passes for every
helper node, and no test that asserts shortcut or label text was weakened.
Update those tests to the new text.

## Then: back to the original plan

After UX6, continue
[DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md) from **Step 4**. That
step is contracts and subworkflows, and it includes fixing the two undetected
Wait Until / Merge deadlocks. Then, in order:

- **Step 4.5:** HTTP off the event loop, with Stop-safe cancellation, and a
  sweeper for run files left by crashed runs;
- **Step 5:** event sources and start triggers, plus the wait-for-event
  decision;
- **Step 6:** the server.

Step 4 needs the owner's go-ahead; ask before starting it unless the owner
has already given it in the session.
