# Meta nodes build — 2026-10-26

Own worktree `/home/makin/src/nw-meta-nodes`, `codex/meta-nodes`, fetched base
`3f365520730493f1e1ecd24ee592befb23ca5ef5`. Owner approved decisions 1–12 and
samples, with Debug opt-in, measured default cap, future-compatible record
shape and repeated-shape case evidence. [Runtime contract](../../integrations/META_NODES.md),
[delivery case](../../delivery_tests/meta-nodes.json).

## Planning and overrides

[Request](approved-workflow_request.md), [feasibility](approved-feasibility.md),
[node map](approved-node_map.md), [numbered decisions](approved-decisions.md)
are preserved planning snapshots from the external samples packet. Their
pending/no-build wording is historical; each has the approval/override header.
The original read-only CLI probes are retained beside them. The new checker
adds structured fields to shared diagnostics instead of parsing English.

## Measurement

[Actual node execution measurement](catalogue-size.json): Compact, All nodes,
Debug off, **50 entries**. Text **34,618 characters / 34,669 UTF-8 bytes**;
compact JSON **49,866 characters/bytes**, including the final envelope.
Default **62,400**, **25.14%** above the larger form; range 512–64,000.
`measure_catalogue.py` regenerates this observation from registered classes.
Filters are still needed for smaller downstream context caps. Detailed/all-debug
results can overflow; overflow has no success publication.

## Real built screens

[Manifest](manifest.json) records 23 SVG/PNG pairs and production source hashes.
`render_screens.py` uses actual NodeFactory classes, production screens and
`frontend/styles.tcss`. No injected node classes or CSS overrides. It refuses
network and persistence calls, checks unchanged configs/data root and confirms
Save/Close remain visible at 80×24. `rasterize.py` makes offline PNG companions
with a local monospace-font substitution. The contact sheet is an overview;
full-size PNG/SVG files retain readable text.

- [Catalogue Parameters](catalogue-parameters-120x40.png),
  [cap](catalogue-parameters-cap-80x24.png),
  [Include debug nodes](catalogue-parameters-debug-80x24.png),
  [Payloads](catalogue-payloads-120x40.png),
  [selector](catalogue-selector-80x24.png).
- [Checker Parameters / long-text preview](check-parameters-80x24.png),
  [Payloads](check-payloads-120x40.png),
  [Check report Vault](check-payloads-report-80x24.png),
  [three source choices](check-source-80x24.png),
  [selector](check-selector-80x24.png).
- [Composition-designer map](check-map-gate-120x40.png),
  [80×24](check-map-gate-80x24.png), [full map](check-map-overview-140x110.png).
  The map is an unexecuted configuration sketch. It stops at the checked draft
  for manual owner review/build; there is no approval/build node. Kind rejection
  and check failure stop on their separate paths.
- [Contact sheet](contact-sheet.png), [built contracts](built-node-contracts.json).

## Checks

A [small two-node example](nodes-example.json) passes the real
`aotn build --check` CLI with an empty temporary data root:
[report](check-built-nodes.json). The checker uses a separate configured valid
draft; it is not interpreting catalogue text as a workflow. This is a check-only
example, not a generation run or saved workflow.

The #124 consistency test reads its historical baseline plus the new
[source contracts](source_contracts.json): **58 registered types**, exact
Spec sources, Continue upstream-only, every compatible upstream writer,
including the optional secondary Check report. The existing mutation test
still proves a missing offered source is detected.

`tests/test_meta_nodes.py` proves shared CLI verdicts, untouched seeded-library
bytes/mtimes, forbidden build/save/execute/subprocess/network calls, cancellation,
source routing, typed outputs, Debug filters, complete records, headroom and
bounded safe error problems. No real generation or live workflow/settings
changes. Full-suite and final artifact results are recorded in
[verification](verification.json) and the delivery case.
