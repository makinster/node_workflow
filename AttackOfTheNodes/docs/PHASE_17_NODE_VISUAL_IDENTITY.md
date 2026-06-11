# Phase 17 - Node Visual Identity And Selector Taxonomy

**Status:** In progress
**Last updated:** 2026-06-10

Phase 17 is not just a cosmetic row-color pass. It is the foundation for the
next node overhaul: clearer node families, reusable subcategory tags, a more
useful node selector, and editor rows that communicate node identity at a
glance without changing runtime behavior.

The current runtime nodes may be redone as this taxonomy settles. Treat existing
node types as implementation inventory, not the final user-facing library.

## User Experience Goal

Users should be able to answer three questions quickly:

- What kind of node is this?
- What capabilities or concerns does it involve?
- Is it quiet utility plumbing, workflow structure, user-facing output, or a
  complex behavior that deserves extra attention?

The selector and editor should use the same language. If a node appears under
the `Inputs` tab with `File I/O` and `Triggered` filters, the editor details
panel should show the same family and subcategories after the node is added.

## Primary Node Families

Each node has one primary family. This family drives selector tabs and the
strongest row identity.

| Family | Meaning | Examples |
|---|---|---|
| Inputs | Get input from an external source on a shorter timescale than long-lived triggers. | Text In, File Read, Text File Read, Web Scrape, User Text Input |
| Flow Control | Change workflow structure, branch routing, merge behavior, waiting, or loop shape. | Branch, Conditional Branch, Merge Beacon, Wait Until, Looping Branch |
| Outputs | Send workflow results to the user, a file, another system, or a branch-ending surface. | Text Output, File Output, active execution-window output |
| Complex | Nested workflows and unique nodes that do not fit cleanly in the other families. | Subworkflow, unique triggers, advanced branch beacons |

`Complex` is a pressure-release family, not a junk drawer. Prefer `Inputs`,
`Flow Control`, or `Outputs` when the node's main role is clear.

## Subcategories

Nodes can have multiple subcategories. Subcategories are filterable capability
tags, not mutually exclusive families.

Initial subcategories:

| Subcategory | Meaning |
|---|---|
| Triggered | Listens, waits, or wakes a workflow/branch when an external condition happens. |
| File I/O | Interacts with files on the user's computer, including file references kept open for later nodes during a run. |
| Internet | Uses network/web access that is not specifically an AI-service call. |
| AI | Uses AI services. API calls for AI are distinct from the `Internet` tag unless the node is specifically browsing/scraping the web. |
| Passive Output | Produces durable or visible output without taking over the execution window. |
| Active Output | Takes over or interrupts the execution window to show/collect user-facing output. |
| Parallel | Can create or coordinate parallel execution paths. |
| Conditional | Depends on state, inputs, predicates, or branch conditions to decide execution. |
| Runtime Resource | Opens or manages a per-run handle such as a file, stream, listener, or browser/session resource. |
| Utility | Helps inspect, transform, wait, log, debug, or pass data through without being a primary workflow concept. |

More subcategories can be added as the node overhaul reveals real need, but do
not create one-off tags for a single node unless it clearly names a future
filter users would seek.

## Metadata Direction

The backend should remain UI-agnostic, but node metadata should expose portable
identity that any frontend can consume:

- primary family, currently compatible with the existing `category` idea;
- zero or more subcategory tags;
- display glyph or icon name;
- optional color hint;
- short selector summary;
- detailed description for the right panel/config surfaces.

Implementation note: `Node` already has optional `icon_name`, `tags`, and
`color_hint` attributes, but `NodeFactory.get_node_types_metadata()` currently
does not expose `category`, `icon_name`, `tags`, or `color_hint`. Phase 17
should close that metadata gap before building selector filters around it.

## Node Selector UX

The selector should become a taxonomy-first picker:

- Top-level tabs: `Inputs`, `Flow Control`, `Outputs`, `Complex`.
- A string match filter remains near the top of the selector.
- Beneath the string filter, show subcategory checkboxes for the active tab.
- The initial keyboard highlight should be the first subcategory control, not
  the string filter.
- The string filter should follow command-mode activation. It should not begin
  typing simply because the selector opened; `/` can jump to it and `E`/Enter
  can activate it.
- The filtered node list appears below subcategory controls.
- Filter options can differ by tab. Only show subcategories that are relevant
  to at least one node in the active family.
- Keyboard navigation must autoscroll cleanly between filter controls, tabs,
  and the node list so the highlighted control is never cut off-screen.
- String filtering and subcategory filtering combine: a node must match the
  active family, active subcategory filters, and any string query.
- Subcategory filters use `AND` semantics. When multiple subcategories are
  selected, show only nodes that have every selected subcategory.

## Editor Row UX

Editor rows should become easier to scan while staying keyboard-stable.

Preferred direction:

```text
| [ | Security camera setup      | ] |
| [ | Inputs - File I/O          | ] |

| { | Security camera trigger    | } |
| { | Complex - Triggered        | } |
```

This is conceptual, not a fixed ASCII contract. The preferred implementation is
to use fixed left/right bracket columns around a text column. That keeps open
and close brackets aligned across rows, gives the center text maximum room, and
lets Textual manage styling without fragile manual spacing. Textual widgets are
fine if they produce a cleaner result than hand-aligned text.

The important requirements are:

- node rows may use two lines when space allows;
- bracket or frame style can differ by primary family;
- brackets/frames align cleanly across rows, preferably with fixed bracket
  columns on either side of the node text;
- the first line emphasizes the user-facing alias;
- the second line shows family plus one or two high-signal subcategories;
- if the second line cannot fit, truncate the visible subcategory text with an
  ellipsis; the full list remains available in the right-side details panel;
- utility/debug/pass-through nodes should be visually quieter;
- validation, breakpoint, selection, execution, and Merge Beacon health colors
  remain more important than decorative family color;
- cursor/highlight behavior and branch selector rows must stay stable.

The right-side details panel should show the node's primary family and all
subcategories. This helps users understand why a node appeared under particular
selector filters.

## Boundary Rules

- Runtime behavior does not change in Phase 17 unless a metadata field is
  needed to describe existing behavior.
- Selector tabs, filter state, row brackets, row colors, and display density are
  frontend concerns.
- Portable node identity metadata belongs on node classes and through
  `NodeFactory` because future frontends also need it.
- File handles, browser sessions, listeners, and similar resources are runtime
  resource concerns for later phases. Phase 17 can name them with metadata, but
  should not implement resource sessions unless that becomes an explicit phase.

## Forward Design Decisions

These choices are settled for the first implementation pass:

- Subcategory filtering uses `AND` semantics.
- The string filter is activate-to-edit, not auto-edit on selector open.
- Subcategory controls are checkboxes.
- Subcategory choices are tab-specific and derived from the active family.
- `Complex` remains partly TBD until the other families are stronger; prefer it
  for structurally unusual nodes such as nested workflows, unique triggers, and
  advanced beacons.
- Outputs use `Passive Output` and `Active Output` tags. A future
  branch-ending output tag can be added if outputs intentionally close branches.
- `AI` and `Internet` stay distinct. A normal AI API call is `AI`; web browsing,
  scraping, or non-AI network access is `Internet`; a web-browsing AI node may
  carry both.
- Existing nodes should receive transitional metadata. Do not overfit the new
  taxonomy to the current node list because many current nodes are expected to
  be redone.

## File Resource Direction

Users should see and configure files by their normal file names/paths. File
input and output nodes should let users choose files in node config where
appropriate, then pass those paths into workflow execution.

Actual file access happens during a run. Future runtime-resource work should
provide a run-scoped owner that can open files, keep access available for later
nodes in the same run, and close resources predictably at run completion. This
may be coordinated by `MasterState`, but should likely live in a focused helper
or execution-session module so `MasterState` does not become the file/resource
manager itself.

## Completion Shape

Phase 17 is complete when:

- the active docs agree on the taxonomy and selector/editor direction;
- `NodeFactory` exposes the metadata needed by the frontend;
- the selector has family tabs and subcategory filters with keyboard-first
  navigation;
- editor rows show stable visual identity for family/subcategory;
- the details panel exposes family and subcategories;
- focused tests cover metadata exposure, selector filtering, row rendering, and
  keyboard/autoscroll behavior.
