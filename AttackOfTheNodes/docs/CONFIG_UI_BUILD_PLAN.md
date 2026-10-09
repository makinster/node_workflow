# Configuration UI build plan — integrated inventory

## Saved workflow follow-up — 2026-10-08

Writer forwarding now handles File Path-only connections. Start has one value
editor and a read-only routing preview; Text Output shows its selected source
and formatted output preview. Text Output continues when connected, restoring
existing Text Output → Wait Until chains; unconnected outputs end naturally,
and End stops explicitly. This supersedes the previous unconditional Text
Output termination policy. See [follow-up evidence](audits/payload_followup_2026_10_08/README.md)
and the latest SESSION_LOG for verification. Owner workflows were not modified.

## Payload/file implementation — 2026-10-07

The requested payload/file build is implemented locally on `main` at `1211e68`
(uncommitted changes). See [the completed contract and migration notes](PAYLOAD_FILE_IO_BUILD_PLAN.md)
and [verification evidence](audits/payload_file_io_2026_10_07/README.md).
Includes File Manager multi-file references, Reader text routing, Writer
prepend/append/newline options, typed source selection, forwarding previews,
Start/Text Output Vault routing, explicit termination and Merge home payloads.
Line-number insertion remains deferred. Native Windows FO7 and the reported
user/host path prefix remain live-verification items, not confirmed fixes.
This status supersedes older planned descriptions below.

Baseline: authoritative checkout, current session integration branch, 37 registered
node types; 36 user-facing/editable types and one intentional internal tombstone.
Start/End are editable compatibility types, not selector additions. File Instance
is retired; File Write, File Viewer and Window Control replace its demo role.

Evidence: [original audit](NODE_CONFIG_UI_AUDIT.md),
[File Output review](FILE_OUTPUT_INTEGRATION_REVIEW.md), and
[current integrated coverage](audits/integrated_2026_10_06/README.md).
This document orders the remaining UI work; the session integration strategy is
[SESSION_INTEGRATION_BUILD_PLAN.md](SESSION_INTEGRATION_BUILD_PLAN.md).

Owner-requested continuation (2026-10-07):
[PAYLOAD_FILE_IO_BUILD_PLAN.md](PAYLOAD_FILE_IO_BUILD_PLAN.md) coordinates stages
1/4 with actual Start/Text Output Vault support, forwarding provenance, typed
source pruning, multi-file Viewer, Writer editing modes, completion-option
removal and Merge carry-forward fixes. It is planned work, not completed scope.
File Viewer is now named File Manager; P2a adds explicit File Reader file-input
and text-output routing to downstream/Vault using the existing Reader node.
Its explicit terminal-node direction supersedes the older optional completion
checkbox policy for this follow-up; old-save migration must be settled first.

## Policy

Source, Parameters, Payloads and Connections describe shared meanings. Display
only sections backed by real capability. Use flat forms for compact nodes and
focused layouts for topology-driven nodes. Metadata and reusable helpers are the
first implementation mechanism; do not create a bespoke screen for each node.
Number visible tabs consecutively. Use dead-drop payload, Vault, Parallel Branch
and Merge Beacon consistently. Describe special values and disabled controls.
Preserve execution semantics and backend/frontend boundaries.

## Stages and completion criteria

| Stage | Work | Verification / status |
|---|---|---|
| 0 — Integrate and repair concrete blockers | Retain pending runtime and Wait Until changes; merge File Output; preserve unknown config; repair form width/description wrapping; preserve Chat temperature zero; fix ambiguous discovery, blocking launch, queued displays, unsupported Window Control forwarding and writer-path warnings. | Implemented in this PR. Real integrated suite, production CSS, cross-branch Vault/file regression and helper checks; counts in SESSION_LOG. Windows live verification still outstanding. |
| 1 — Truthful shared capability composition | F01: inventory the genuine legacy declaration consumers (User Text Input writes, Branch Vault seeds, node-owned setters/counters) and gate generic controls for the other legacy nodes. Keep saved unrelated config; do not implement fictitious Vault operations to justify controls. | For every affected type, absence/presence checks plus execute/save/reopen/Cancel. Verify backward-compatible real declarations. Treat as a focused shared-helper change with explicit metadata contracts. |
| 2 — Applicable sections and navigation | F05: derive visible sections from actual controls and topology; omit empty tabs. Prefer compact forms; maintain per-tab focus, scrolling and consecutive numbering. Wait Until remains Wait/Connections. | Production CSS at 60/100/140; W/S rows and list-boundary exit, A/D within rows, numbered tabs, E/Enter, editing digits/navigation letters, save/cancel. Verify Start/End and Merge Beacon exclusions intentionally. |
| 3 — Schema truth and validation | F06/F07/F08: conditional fields, ignored Random Number Payload field, positive/nonnegative numeric validation, HTTP timeout semantics, labels and zero descriptions. Change specs and executable schema together; generator defaults need review before removing fields from generated custom nodes. | Selected-source/mode conditional states, invalid save retention, zero/default values, unrelated config retained. No runtime behavior changes solely for visual simplicity. |
| 4 — Routing and descriptions | F09/F10/F11/F12: define which upstream port Chat forwards; explain simulated AI nodes and omit inert secret controls; truthful Echo/Repeat descriptions; resolve undeclared count/visits ports separately from UI cleanup. | Focused runtime evidence and saved graph compatibility. Port-shape changes require a separate migration decision. |
| 5 — File/window capability UX and owner review | FO-R5: expose unsupported platform explanations and action preflight warnings; align viewer keyboard navigation; document WSL runtime capabilities, file-loop window reuse and legacy-demo recovery. Execute existing FO7 Windows protocol. | Linux/fake adapter tests do not close FO7. Owner tests real Windows apps, monitors, terminal hosts and focus interactions; no claim of complete window support before that. |

## Deliberately deferred bugs and decisions

Owner-requested shared visibility/scrolling slice implemented locally (2026-10-06):
legacy Vault lists and write fields stay hidden until enabled; inactive standard
routing fields and Merge carry-forward selection stay hidden with their labels.
Temporary hiding preserves entered values. Configuration starts on its first
field, and only the highlighted field drives scrolling; initialization events
and next-neighbour previews no longer move the view. This addresses a focused
part of stage 2, not stage 1's runtime capability audit or the remaining empty-tab
cleanup. Verification and local publication state are recorded in SESSION_LOG.

The follow-up [visibility/scrolling audit](NODE_CONFIG_VISIBILITY_SCROLL_AUDIT.md)
covers every editable type. It also hides Text Output's optional prompt,
Set Variable's inactive literal, Conditional's inactive variable name, HTTP's
GET body, and unavailable legacy write toggles. Node Config owns its scrolling
without competing deferred centering/reveal requests. These are targeted stage
2/3 repairs; numerical validation, ignored fields, empty tabs, runtime capability
composition and platform explanations are still separate work.

- **P1 F01:** misleading legacy generic Vault controls remain on nodes whose
  execution does not use them. Requires a coordinated capability contract;
  do not infer support from having a single output port.
- **P2 F05–F07:** empty four-tab composition, missing source/mode visibility,
  and Random Number's ignored Payload field remain. Fix shared composition
  and generator/custom-node schema alignment together.
- **P2 F08:** generic invalid numbers can coerce to zero; negative Sleep is
  accepted then clamped; HTTP zero timeout becomes its default. Chat zero
  temperature is fixed. Define timeout validity before changing semantics.
- **P2 F09:** Chat forwarding prioritizes document/prompt and ignores other
  context slots; enabled blank keys can silently do nothing. Needs a clear
  routing/source policy and validation.
- **P2 F10–F12:** inert simulated-AI secrets, misleading Echo/Repeat descriptions,
  and undeclared count/visits outputs remain documented in the audit.
- **P2 FO-R5:** unsupported window options need visible explanations and
  Window Control capability preflight. Current fallback is intentional,
  but configuration promises need clearer presentation.
- File Reader typed-reference input is a potential new capability, not a
  defect fix; keep its current configured-path behavior until explicitly scoped.
- Window discovery still relies on a single-new-window or unique-title heuristic;
  ambiguity no longer chooses randomly. HWND reuse, application window reuse,
  64-bit parent-process handle discovery and live monitor behavior remain FO7
  review targets. Large synchronous file writes and reading very large viewer
  files remain performance follow-up work; this PR offloads window launch only.

The chosen viewer policy for this PR is FIFO, scoped to the displayed run.
Input/recovery modals take priority; retired-run queued requests are dropped on
reset. Nodes continue executing after display requests. A searchable history,
queue limits and content snapshots would be later product work.

## Final verification gate for later stages

For each stage: targeted behavioral regressions and helper checks, actual mounted
controls in meaningful combinations, config save/reopen and Cancel, production
CSS at all three widths, then the wider relevant suite. Record actual verification
and uninspected/live-review limits in SESSION_LOG. Historical audit counts are not
new results. Keep the original evidence alongside later captures to show progress.
