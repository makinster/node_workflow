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
| Legacy nodes (no `inputs:` block) | Silent fallback to current flat Source tab |
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

## 3. Config Source Tab — Vault Conditional Dropdown (Track B Phase 4b)

When a port's source is set to `Vault`, a **second `Select` widget** appears
immediately below the source selector, populated with type-filtered vault keys.

```
Text Prompt*  [string]
├─ Source ▶  [ Upstream             ▼ ]

Document  [string]
└─ Source ▶  [ Vault                ▼ ]
        └─< Vault key:  [ document.pdf [file]    ▼ ]
                                            ↑ conditional widget
                                              appears when Vault selected
```

- Vault dropdown shows only entries whose stored `type_tag` matches the port's
  `data_type`. Incompatible entries are hidden entirely.
- When `data_type` is `any`, no filtering — all entries shown.
- Widget is generated/removed reactively via `on_select_changed`.
- Format: `key [type]` — e.g., `document.pdf [file]`.
- **Depends on**: Typed Vault Entries backlog item (stored `type_tag` per key).

---

## 4. Config Source Tab — Upstream Description Hint (Track B Phase 4b)

When a port's source is `Upstream`, show the connected upstream output's
description inline below the source row.

```
Text Prompt*  [string]
├─ Source ▶  [ Upstream             ▼ ]
└─  Http Request
        └─>  Http Result  [bool]
             "200 OK, 1.2kb body"   ← last captured value preview if available
```

- Upstream alias: user alias → `default_alias` from metadata → node type with
  underscores stripped and title-cased.
- Output port name and `[type]` rendered on the sub-row.
- Last captured value shown if `memory_bank` holds a value; omit if absent.
- Walk uses existing `trace_transient_producer()` + new port `description` field.

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
| **Vault labels** | `[type]` labels in vault SelectionList | Blocked on Typed Vault Entries |
| **Source tab vault dropdown** | Conditional vault key selector | Deferred (Track B Phase 4b) |
| **Source tab upstream hint** | Inline upstream description | Deferred (Track B Phase 4b) |
| **⚠ badge** | Node card validity indicator | **Done (2026-06-22)** |
| **Drill-in nav** | Quick-list in detail panel + GroupBrowserScreen deferred | **Done (2026-06-22)** |
