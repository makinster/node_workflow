# Payload and File I/O integration audit — 2026-10-07

Authoritative checkout `/home/makin/src/node_workflow`, branch `main`, base
`1211e68`. Implementation is uncommitted. OneDrive recovery files and unrelated
untracked files were preserved. This audit covers the combined changes in
[the build plan](../../PAYLOAD_FILE_IO_BUILD_PLAN.md).

## Evidence and scope

`verify_ui.py` reuses the previous read-only synthetic capture harness with a
new output directory; earlier audit evidence is untouched. `summary.json`
contains the aggregate result; `evidence.json.gz` contains metadata, selector
entries, widget inventories, conditional states and save/reopen/Cancel records.
No owner workflow or settings file is loaded or saved by the harness. Run it
with the repository venv. The snapshots are headless production-CSS checks,
not proof of native Windows or interactive terminal behavior.

All 37 registered types were inventoried; 36 editable types were mounted at
60, 100 and 140 columns (108 mounts). All 36 Cancel checks retained the original
node, all 72 saves preserved unrelated configuration, and all 72 second saves
matched the first. Conditional control changes produced no exceptions.

Focused tests cover typed producer/consumer choices, actual forwarded preview
values (including captured None), unavailable saved selections, Manager row
editing/selection, file-reference identity, deletion/undo/reload, error modal
keyboard navigation, Content editing, Windows/WSL syntax, Reader content and
routing, Writer insertion/newlines, Manager batch validation, and migration.
The integration regression executes both home and sibling Merge payload
choices through a saved/reloaded multi-file, parallel Reader/Writer workflow;
it also checks terminal output and deletion/restoration of declared file keys.

The audit corrected missing string/number metadata, Writer forwarding-port
provenance, User Text Input's declared Vault type, disabled downstream source
eligibility, unsupported generic legacy Vault controls, and shared mutable
node defaults. Legacy declaration data remains readable for old workflows;
new generic controls are capability-gated.

## Verification

**784 full-suite tests passed in 121.97s**, including the full debug suite.
The final saved-forwarding runtime/picker correction passed 39 focused tests
before that full rerun. Mounted evidence covers 163 conditional states.
Application/helper compile checks and `git diff --check` pass. Helper UI
contracts pass for File Reader, File Writer, File Manager, Start and Text Output;
custom runtime implementations are retained alongside the reviewed specs and
generated regression tests. Original Reader path regressions are preserved in
`tests/test_file_reader_paths.py` rather than overwritten by generated tests.

## Remaining boundaries

- Insert at a numbered line is an explicit future feature, with no inert UI.
- The exact quoted Windows path normalizes to the existing `/mnt/c/...` file.
  The converter does not construct a `makin@kelly:` prefix; its observed live
  origin is unconfirmed. Configuration preserves the entered path, while
  filesystem references/events use the normalized local path.
- Native Windows/window placement and owner's live terminal checks remain FO7.
- Merge retains five fixed input ports; the UI reports capacity rather than
  silently reusing an occupied input. Parallel Vault readers require ordering.
- Writer joins prepend/append text exactly; users supply separators or opt in
  to interpreting `\n` and `/n`. File references do not snapshot file contents.
