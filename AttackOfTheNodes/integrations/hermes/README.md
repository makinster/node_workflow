# Hermes H0 adapter

Repository implementation of the [H0 contract](../../docs/integrations/HERMES_H0_DRAFT.md),
authorized by the owner after C1–C7 in PR #102. Standard-library Python and
Bash; POSIX process groups and `flock` require Linux/WSL. No engine changes.
These files are staged for owner review, with no installation or cron activation.

- `_aotn_common.sh`: sourceable `aotn_cron_run` function, selecting the exact
  saved workflow name from `aotn-<slug>.sh`. It rejects arguments and invalid
  names, changes to the absolute project root and execs the absolute interpreter.
- `_aotn_run.py`: subprocess/JSON adapter, isolated cron library, timestamp,
  per-slug nonblocking lock, concurrent bounded pipe draining and exit handling.
- `aotn-h1-heartbeat.sh`, `aotn-h2-http-watchdog.sh`: entry scripts for later
  copying/linking to `/home/makin/.hermes/scripts/`, alongside both shared files.
  Entry scripts honor `HERMES_HOME` (default `/home/makin/.hermes`).
- `h1-heartbeat.json`, `h2-http-watchdog.json`: `aotn build` definitions, with
  quiet End nodes. H2's loopback URL is an example; choose the real endpoint
  deliberately before building into the cron library.

Production paths in the shared function are explicit:
`/home/makin/src/node_workflow`, its `.venv/bin/python`, and the separate
`/home/makin/.local/share/aotn-cron` data directory. The adapter itself accepts
absolute paths for checkout-local verification; it rejects the repository app
and workflow directories as data destinations. No PATH interpreter lookup or
AOTN imports occur in the adapter. Entry filenames select saved names; they
never build or replace workflows.

From the repository root, review/build into a disposable directory:

```bash
scratch=$(mktemp -d /tmp/aotn-hermes.XXXXXX)
/home/makin/src/node_workflow/.venv/bin/python AttackOfTheNodes/main.py build AttackOfTheNodes/integrations/hermes/h1-heartbeat.json --data-dir "$scratch"
/home/makin/src/node_workflow/.venv/bin/python AttackOfTheNodes/integrations/hermes/_aotn_run.py --workflow-slug h1-heartbeat --project-root "$PWD" --data-dir "$scratch" --python /home/makin/src/node_workflow/.venv/bin/python
```

The adapter consumes `--json`, renders outputs and named values like the text
CLI, and emits zero stdout bytes for a successful empty report. Child diagnostics
stay on stderr. Each emitted stream is escaped then capped at 3,500 UTF-16 units,
including its run-ID truncation tail. `[SILENT]` variants and literal `MEDIA:`
are neutralized; only JSON-looking lines get `| `, including after non-LF line
separators. Ordinary heartbeat text is unchanged.

Natural child exits are preserved (signals use 128 + signal). Adapter failures
are 70, overlap is 75, deadline is 124, and external INT/TERM are 130/143. The
fixed 100-second deadline sends process-group INT at 95 seconds, then starts
KILL cleanup at 99, reserving the final second for reaping. External stops allow
five seconds including that final cleanup budget. Linux uses subreaper adoption
and `/proc` ancestry to kill/reap descendants even after `setsid()`; other POSIX
systems retain bounded process-group cleanup. Linux subreaper setup failure
prevents spawning. Locks remain held
through cleanup; streams retain at most 1 MiB of report and 64 KiB of diagnostics.
Full output remains in AOTN run records, not in a Telegram receipt.

A persistent marker records unconfirmed cleanup before spawning. Confirmed
cleanup clears it; a crash or failed cleanup leaves it stale. Cleanup failures
exit 70, and subsequent ticks report 75 without starting a run. Verify/terminate
prior descendants before clearing the stale file's contents under
`<cron-data>/.hermes-locks/<slug>.lock`; preserve its inode and never unlink an
actively locked file.

`tests/test_hermes_adapter.py` covers every H0 acceptance-table row as adapter
subprocesses, using the real CLI plus loopback HTTP for H1/H2 and controlled
child programs for malformed reports, limits, lock ownership and signals.
Timing cases use a subprocess launcher with shortened module constants; there
is no production environment/CLI/workflow timing override. A separate assertion
checks the production 100/5-second constants. No external network is needed.

Owner approval and deployment remain separate. This implementation does not
change `cron.wrap_response` (C4 says off), write to `~/.hermes`, create jobs,
send messages, implement the later shared folder/outbox, or claim delivery.
Recheck the installed Hermes interface and the draft's activation criteria
before enabling any schedule.
