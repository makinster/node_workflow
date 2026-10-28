# Test suite speed — 2026-10-27

Base `4f1f5e7`, branch `codex/faster-tests`, own worktree
`/home/makin/src/nw-faster-tests`. Runtime code and production timing defaults
are unchanged. [Machine-readable measurements](measurements.json) include
commands, pytest totals and the slowest fifteen for each run.

## Wall time

All commands run from `AttackOfTheNodes/` using the authoritative checkout's
Linux venv. Python 3.14.4, pytest 9.1.0, Textual 8.2.7, xdist 3.8.0,
execnet 2.1.2; 24 available CPUs / auto workers. Times below include process
startup and exit, measured outside pytest.

| Run | Before | After |
|---|---:|---:|
| Full serial | 694.25 s | 526.10 s |
| Full `-n auto` | 133.16 s | 35.48 / 35.45 / 35.38 s |
| Quick `-n auto -m "not slow"` | not measured | 29.68 s |

The owner's independent original serial measurement was **657 s**. Our original
serial run reported 674.19 s inside pytest and 694.25 s including shutdown;
it overlapped the initial parallel diagnostic and brief focused checks, so its
serial improvement is not a controlled speedup ratio. Optimized serial was
508.57 s inside pytest / 526.10 s including shutdown.

The controlled original parallel run used original test bytes plus the new
isolation/capture/scheduling harness and installed xdist, with no competing
pytest process. It collected the original 3,137 cases, excluding the new isolation
test. Every replaced test file was restored byte-for-byte afterward. An earlier
overlapping original parallel diagnostic also passed in 130.51 s. Original main
has no xdist dependency, so a pristine `-n auto` command was unavailable.

**Three consecutive optimized full parallel runs passed: 3,127 tests each, no
failed tests, reruns or fork warnings.** Quick: 3,083 passed, 44 slow cases
excluded. Serial: 3,127 passed. The final serial/quick measurements also passed.

## What changed without removing behavior coverage

- Collection and every test get disposable data/Hermes roots, including
  import-bound persistence aliases. Subprocesses inherit the per-test root.
  Two tests reuse identical workflow/settings names and check parent/child paths.
- Logging handlers/levels are restored per test. Saved-values concurrency uses
  spawn and explicit child lock configuration, retaining all worker/count checks.
- Stash still checks every declared selector, including nested schemas and model
  pickers, through the actual form factory and refusal guard. A small mounted
  app tests each selector kind with real keys; existing integration cases remain.
- Short real-process deadline tests keep hostile detached descendants, deadline
  status, lock/marker release, kill and reap assertions. Test-only runpy wrappers
  shorten subprocess timing constants. One full production 25-second deadline
  remains, marked `slow`. No application timing override was added.
- Twenty real subworkflow calls now have exact weak-reference release checks
  instead of broad interpreter-heap scans. No call count was reduced.
- Geometry retains all original sizes; extra sizes are marked `slow`. Eighteen
  duplicate non-layout size cases were removed while retaining other parameter
  axes. Eight cases were added: four from splitting size loops, one mounted
  Stash check, one short deadline case and two isolation cases. Net: 3,137 → 3,127.
- Default scheduler is work-stealing; output capture replaces unconditional `-s`.
  Fake HTTP servers use a short shutdown polling interval.

## New top fifteen — serial

Durations are pytest **call-phase** times, not the external wall measurement.
The report JSON also retains the parallel-run lists, which differ under load.

| Seconds | Test |
|---:|---|
| 24.13 | `tests/test_telegram_launcher.py::test_launcher_deadline_kills_and_reaps_descendants[production-25s]` |
| 5.47 | `tests/test_editor_delete_group_ui.py::test_picker_scrolls_to_last_path_and_buttons_stay_visible[140]` |
| 5.44 | `tests/test_editor_delete_group_ui.py::test_picker_scrolls_to_last_path_and_buttons_stay_visible[60]` |
| 5.43 | `tests/test_editor_delete_group_ui.py::test_picker_scrolls_to_last_path_and_buttons_stay_visible[100]` |
| 4.38 | `tests/test_hermes_adapter.py::test_overlap_per_slug_and_cleanup_lock` |
| 3.59 | `tests/test_node_config_visibility_scroll.py::test_llm_initial_focus_and_scroll_follow_highlight_only[140]` |
| 3.40 | `tests/test_node_config_visibility_scroll.py::test_llm_initial_focus_and_scroll_follow_highlight_only[60]` |
| 3.32 | `tests/test_node_config_visibility_scroll.py::test_llm_initial_focus_and_scroll_follow_highlight_only[100]` |
| 3.27 | `tests/test_source_menu_audit.py::test_actual_ui_sources_and_visible_fields_for_all_standard_ports[chat_completion_node]` |
| 3.07 | `tests/test_small_wins_ui.py::test_configured_preview_full_editor_save_cancel_and_stash` |
| 2.86 | `tests/test_wait_until_ui.py::test_wait_layout_navigation_and_clean_save[60]` |
| 2.80 | `tests/test_wait_until_ui.py::test_wait_layout_navigation_and_clean_save[100]` |
| 2.78 | `tests/test_wait_until_ui.py::test_wait_layout_navigation_and_clean_save[140]` |
| 2.65 | `tests/test_long_text_ui.py::test_unbroken_line_preview_full_value_and_hidden_source_are_preserved` |
| 2.53 | `tests/test_stash_current_focus.py::test_node_p_after_edit_preserves_form_and_workflow_dirty_state[checkbox]` |

The remaining adapter overlap test intentionally exercises its existing cleanup
path. Layout/scroll tests and the single real long deadline now dominate the list.

## Reproduce and review

Install `requirements-dev.txt`, then run from `AttackOfTheNodes/`:

```bash
python -m pytest -n auto
python -m pytest -n auto -m "not slow"
python -m pytest -n 0 --durations=15
```

Reviewers must run the **full** set before merge; quick skips extra layout sizes
and the production-duration check. See [Contributing](../../CONTRIBUTING.md#parallel-tests-and-isolation)
for fixture rules and test-only timing seams. No real model or external API calls
were made for this work.
