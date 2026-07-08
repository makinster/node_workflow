# I/O Contract UI Design

**Status:** Adopted 2026-06-22. Implementation in progress on Track B.
**Audience:** Coding agents implementing Track B frontend changes.
**See also:** `NODE_STANDARDIZATION_HANDOFF.md` for the backend contract shape.
`UI_QUICK_REFERENCE.md` for command-nav rules. `TUI_DESIGN.md` for full screen specs.

---

## Design Decisions (resolved)

| Decision | Ruling |
|---|---|
| Type mismatch display | Option B: amber `[type]` label if a mismatch slips through; primary prevention is dropdown filtering |
| Vault incompatibles in dropdown | Hide entirely — no divider, no ghost entries |
| Untagged legacy vault entries | Treated as `string`-compatible (shown for `string`/`any` ports, hidden for `file`/`ai_session`) — hiding them everywhere would empty most dropdowns (2026-07-07) |
| Legacy nodes (no `inputs:` block) | Silent fallback to current flat Source tab |
| Irrelevant vs locked controls | Irrelevant fields are **hidden** (`visible_when`); grey-out (`enabled_when`) only for locked controls like the required-unless-transient vault write (2026-07-07) |
| Mode-driven required inputs | An input that becomes mandatory in a particular mode uses `required_when` (adds `*`) and `section_when` (retitles its section header, e.g. Optional → Required). `force_value_when` exists for locking a select to a value but is not used where the user should keep source choice (2026-07-08) |
| Output model | One designated **Downstream node payload** (editable name/description) per node; all other outputs are **keyed Vault payloads** of a declared type (editable key + description, `Disable output` checkbox when optional). Single `Forward incoming payload unchanged` checkbox replaces per-output send/save checkboxes. Payloads tab composed from `output_port_metadata.to`, not schema fields (2026-07-08) |
| Payload names show type | Wherever an incoming/outgoing payload name is rendered, the data type follows in parentheses — `Result (string)` (2026-07-08) |
| Redundant vault-write UI | Standard-model nodes render only the Result Routing fields; legacy Write to Vault rows and reveal checkboxes are suppressed, with the validator deriving declarations from standard-model config (2026-07-07) |
| ⚠ badge trigger | Option A: driven by last `V` (validate) run; option B (continuous) is a backlog item |
| Tab-sticking fix scope | General: scroll inside each `TabPane`, `.tab-scroll` CSS class, audit all tabbed UIs |

---

## 1. Contract Panel — Node Selector (Track B Phase 1)

The existing single-line `#node-detail` `Static` is replaced by a **master-detail horizontal split** below the filter row.

**Taxonomy (2026-06-22):** The selector now has **five tabs mapping 1:1 to the
five backend families**: `In` → Inputs, `Flow Control`, `Utility`, `Out` →
Outputs, `Complex` (hotkeys 1–5, in that order). The earlier combined `I/O` tab
with an Input/Output segmented toggle is **retired**. Rationale: Outputs is
growing its own identity — live UI-display nodes that render data on screen
during workflow execution — so it warrants a dedicated tab rather than sharing
one with Inputs. Tab display labels (`In`/`Out`) are abbreviated; `TAB_FAMILY`
in `node_selector.py` maps each to its `primary_family` value. This also closes
the long-standing "Selector Family Taxonomy Reconciliation" backlog item.

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ Add Node                                                         │
│ [1-In] [2-Flow Control] [3-Utility] [4-Out] [5-Complex]         │
│ [Filter nodes_________________________________________]          │
│ ┌──────────────────────┬───────────────────────────────────────┐ │
│ │  [ Text Prompt Node ]│ Text Prompt Node                      │ │
│ │  { AI Processing }   │ Sends a text prompt to an AI model    │ │
│ │  [ Vault Write     ] │                                       │ │
│ │                      │ Required Inputs:                      │ │
│ │  ── AI ───────────── │   text_prompt*  [string]              │ │
│ │  [ Prompted LLM    ] │   The starter prompt for the LLM chat │ │
│ │                      │   └─< upstream  vault  configured     │ │
│ │                      │                                       │ │
│ │                      │ Optional Inputs:                      │ │
│ │                      │   document  [string]                  │ │
│ │                      │   Optional doc appended after prompt  │ │
│ │                      │   └─< vault                          │ │
│ │                      │                                       │ │
│ │                      │ Required Outputs:                     │ │
│ │                      │   response  [string]                  │ │
│ │                      │   LLM chat response                   │ │
│ │                      │   └─> vault                          │ │
│ │                      │                                       │ │
│ │                      │ Optional Outputs:                     │ │
│ │                      │   result  [bool]                      │ │
│ │                      │   Success/failure signal              │ │
│ │                      │   └─> downstream                     │ │
│ └──────────────────────┴───────────────────────────────────────┘ │
│ W/S move  A/D within row  1-4 tabs  E add  / filter  ESC close  │
│ [Cancel]                                                         │
└──────────────────────────────────────────────────────────────────┘
```

**Sizing:** List 40%, detail panel 60%. Both expand to fill available height.

### Port Row Format (3 lines per port)

```
  port name*  [type]
  Port description text
  └─< source1  source2      (inputs)
  └─> dest1  dest2          (outputs)
  ↔ pass-thru               (pass-through ports)
```

- `*` on the port name when `required: true`.
- `[type]` label in VS Code Dark+ teal `#4EC9B0` via Rich markup.
- Underscore-to-space in port names (e.g., `text_prompt` → `text prompt`).
- Sources/destinations: space-separated, lowercase.
- **Empty sections omitted entirely** (no "none" placeholder).
- Port separator: blank line between ports in the same section.

### Group Highlight (when a group row is highlighted)

```
{ AI Processing }
Sends prompts to an AI model and returns responses

3 node types:
  [ Prompted LLM ]
  [ Chat History LLM ]
  [ Summarizer ]

E = open picker  D/→ = quick list
```

### Empty / No-match State

```
(wow, it's empty in here)
```

---

## 2. Tab-Sticking Fix (All Tabbed UIs)

**Bug:** `TabbedContent` is wrapped inside a `VerticalScroll`. Scrolling the form
makes the tab bar disappear off-screen.

**Fix:** Scroll lives **inside** each `TabPane`, not outside `TabbedContent`.
`TabbedContent` and its tab bar stay pinned at the top.

```
Before:
  ModalCard
    Label (title)
    VerticalScroll          ← tabs scroll away with content
      TabbedContent
        TabPane 1: [content]
        TabPane 2: [content]
    ButtonRow

After:
  ModalCard
    Label (title)
    TabbedContent           ← pinned
      TabPane 1:
        VerticalScroll      ← scroll inside the pane
          [content]
      TabPane 2:
        VerticalScroll
          [content]
    ButtonRow
```

**CSS pattern:**
```css
.tab-scroll {
    height: 1fr;
    overflow-y: auto;
}

#node-config-tabs {
    height: 1fr;
}
```

**Non-tabbed modal paths** (Merge node, Branch End node) keep a single flat
`VerticalScroll(id="node-config-scroll")` so existing scroll-helper methods
fall back correctly.

**`_scroll_container()` helper pattern** (applies to all tabbed screens):
```python
def _scroll_container(self):
    try:
        tabbed = self.query_one("#node-config-tabs", TabbedContent)
        active_id = tabbed.active
        if active_id:
            pane = self.query_one(f"#{active_id}", TabPane)
            scrolls = list(pane.query(".tab-scroll"))
            if scrolls:
                return scrolls[0]
    except Exception:
        pass
    try:
        return self.query_one("#node-config-scroll")
    except Exception:
        return None
```

---

## 3. Config Source Tab — Vault Conditional Dropdown (Track B Phase 4b) — **Done (2026-07-07)**

When a port's source is set to `Vault`, a **second `Select` widget** appears
immediately below the source selector, populated with type-filtered vault keys.

```
── Required Inputs ──────────────────
Prompt source:  [ Vault ▼ ]
Prompt Vault key:  [ notes [string]  ▼ ]   ← hidden unless Vault selected
```

Implementation (differs slightly from the original sketch):

- The vault key field is a schema field (`<port>_vault_key`) carrying a
  `vault_type` key (the port's `data_type`) and
  `visible_when: {<port>_source: "Vault"}`; `form_generator.build_form`
  renders it as a `Select` over `vault_keys_by_type` supplied by
  `NodeConfigScreen._vault_key_options()`. Hidden/shown by the existing
  dynamic-rule engine, not by reactive widget mount/unmount.
- Options: persisted vault entries with a compatible `type_tag` **plus keys
  declared by workflow writers** (legacy `membank_outputs`, standard
  `vault_write_key`, session keys) so wiring works before the first run.
- Compatibility: exact tag match; **untagged legacy entries also satisfy
  `string`**; `any` accepts everything. Incompatible entries hidden entirely.
- **Eligibility (2026-07-07):** declared keys whose only writers are
  downstream of the configured node on the same branch — or the node itself —
  are excluded (they cannot exist when the node runs). Parallel-branch
  writers stay listed; branch timing is the validator race warning's job.
- **Option pruning (2026-07-07):** a source option that would reveal an empty
  typed dropdown (`Vault`, `Continue AI session`) is dropped from the source
  selector; a previously saved selection stays selectable so old configs
  display faithfully.
- Format: `key [type]`; untagged keys render bare. A configured value that no
  longer resolves renders as `key (not declared)`.
- The helper generator emits this pattern for every `input_sources` /
  `inputs:` port that allows the Vault source.

---

## 4. Config Source Tab — Upstream Description Hint (Track B Phase 4b) — **Done (2026-07-07, as Incoming Payload block)**

Implemented as a single auto-revealed **Incoming Payload** block at the top of
the Source tab (below alias/description) rather than per-source-row hints —
one compact entry per connected input port:

```
Incoming Payload
  prompt  [string]  <- Text Input > default
  <payload description, when declared>
  Payload: default (str): "last captured value"   ← when memory bank holds one
```

- Producer chain via `trace_transient_producer()`; payload data type from the
  producer's output-port metadata; captured value truncated for display.
- Rendered as a plain read-only `Static` — **keyboard navigation skips it**
  (2026-07-07); it is informational, not interactive.
- Replaces the "Reveal upstream payload" / "Reveal Vault payload" checkboxes
  for standard-model nodes (always visible when connected). Legacy nodes keep
  the old reveal-checkbox layout.

---

## 5. ⚠ Badge — Node Cards (Track B Phase 4c)

A `⚠` glyph on the editor node card when the last validator run (`V`) marked
this node as having unsatisfied required inputs.

- **Option A (implemented):** Driven by last `V` run result stored in workflow state.
- **Option B (backlog):** Continuous background check — see `PROJECT_BACKLOG.md`.
- Required fields in config also use an amber accent color on their label.

---

## 6. Selector Drill-in Navigation (Track B Phase 3 — deferred)

When a group row is highlighted:
- `E` / Enter → opens `GroupPickerScreen` (current behavior, keep as-is).
- `D` / → → moves cursor into a 6-item quick-list in the right detail panel
  (top-6 frequency-sorted; alphabetical default). `E` selects from there.
  `A` / ← returns focus to the left list.

A richer `GroupBrowserScreen` (separate full-screen split) is planned but
deferred. The existing `GroupPickerScreen` modal remains in use until then.

---

## 7. Implementation Phases

| Phase | Scope | Status |
|---|---|---|
| **Tab fix** | `NodeConfigScreen`: scroll inside TabPane, `.tab-scroll` CSS | **Done (2026-06-22)** |
| **Selector panel** | Master-detail split + file-tree contract render | **Done (2026-06-22)** |
| **Vault labels** | `[type]` labels in vault SelectionList | Superseded — legacy SelectionList retired for standard-model nodes; typed labels live in the §3 dropdowns |
| **Source tab vault dropdown** | Conditional vault key selector | **Done (2026-07-07)** |
| **Source tab upstream hint** | Inline upstream description | **Done (2026-07-07, Incoming Payload block)** |
| **⚠ badge** | Node card validity indicator | **Done (2026-06-22)** |
| **Drill-in nav** | Quick-list in detail panel + GroupBrowserScreen deferred | **Done (2026-06-22)** |
| **Editor details panel** | Configured-instance contract in selector's layout | **Done (2026-06-23)** |
| **Standard-model config layout** | Inline alias, auto Incoming Payload, Required/Optional sections, self-labeled checkboxes, hidden-until-relevant gating, compact Outgoing summary, no legacy membank/reveal sections | **Done (2026-07-07)** |

### Editor Details Panel (2026-06-23)

The editor's right-hand `#node-details` panel was reformatted to reuse the
selector's contract layout and labeling, specialized to the configured node
instance. Shared helpers live in `frontend/io_contract.py` (`TYPE_COLOR`,
`type_label`, `wrap_dim`) and are used by both screens.

```
Name: <alias> (<id>)
Description: <node description>
Family: <primary_family>
Tags: <comma-separated tags, blank when none>

Depth: <visible branch depth>
Breakpoint: <on|off>
Avg Time: <avg run timing, or - >

Inputs:
  <input name>  [type]
  <description>
  └─< <configured upstream producer | allowed source kinds>

  <vault key>  [vault]
  <description>
  └─< vault

Outputs:
  <output name>  [type]
  <description>
  └─> <configured downstream target | ↔ pass-thru | allowed dest kinds>
```

- No required/optional split — the editor shows the instance as wired/configured.
- The `└─<` / `└─>` line names the **configured** producer/target node(s) when
  the port is connected; otherwise it falls back to the port's allowed source/
  destination kinds (or `↔ pass-thru` in bold for pass-through outputs).
- Input/output port names honor config overrides (branch path labels, transient
  output overrides); `[type]` comes from port metadata.
- Vault reads (`membank_inputs`) and writes (`membank_outputs`) render as
  `key [vault]` entries with `└─< vault` / `└─> vault`.
- Retired the old `Kind:` / `Subcategories:` / `Step:` / `About:` /
  `Transient Source:` labels.
