# Hermes H0 adapter

Repository implementation of the [H0 contract](../../docs/integrations/HERMES_H0_DRAFT.md),
authorized by the owner after C1–C7 in PR #102. Standard-library Python and
Bash; POSIX process groups and `flock` require Linux/WSL. No engine changes.
These files are staged for owner review, with no installation or cron activation.

**Install (owner or Hermes, 2026-10-21):** Hermes v0.14 rejects scripts whose real path is
outside `$HERMES_HOME/scripts`, so the files are **copies**, not symlinks. Run
`bash /home/makin/src/aotn-live/AttackOfTheNodes/integrations/hermes/install.sh` to copy the
six files (entry scripts executable), and `install.sh --check` to see whether the installed
copies still match the live checkout (exit 1 when they differ). Rerun it after each `pull`.

- `_aotn_common.sh`: sourceable `aotn_cron_run` function, selecting the exact
  saved workflow name from `aotn-<slug>.sh`. It rejects arguments and invalid
  names, changes to the absolute project root and execs the absolute interpreter.
- `_aotn_run.py`: subprocess/JSON adapter, isolated cron library, timestamp,
  per-slug nonblocking lock, concurrent bounded pipe draining and exit handling.
- `aotn-h1-heartbeat.sh`, `aotn-h2-http-watchdog.sh`: entry scripts for later
  copying/linking to `/home/makin/.hermes/scripts/`, alongside both shared files.
  Entry scripts honor `HERMES_HOME` (default `/home/makin/.hermes`).
- `_aotn_drain.py`, `aotn-drain-home.sh` (C1/C3): the outbox drain. A no-agent
  Hermes job every 5 minutes prints one digest of the messages Notify me queued
  for the Send to name in the entry's file name (`aotn-drain-<name>.sh`; copy it
  for another name, so `drain-` is not a workflow slug). Reads `$HERMES_HOME/aotn`
  (`HERMES_HOME` defaults to `~/.hermes`), the same rule the nodes follow; if you
  move Hermes, set `HERMES_HOME` for AOTN too. Formats and
  the per-tick contract: [Hermes shared folder](../../docs/integrations/HERMES_SHARED_FOLDER.md).
  Creating the Hermes job is an owner action; nothing is scheduled by this repository.
- `h1-heartbeat.json`, `h2-http-watchdog.json`: `aotn build` definitions, with
  quiet End nodes. H2's loopback URL is an example; choose the real endpoint
  deliberately before building into the cron library.

Production paths in the shared function are explicit: the live checkout
`/home/makin/src/aotn-live` (a worktree on branch `live`, tracking main; update it on
purpose with `git -C /home/makin/src/aotn-live pull`), the shared
`/home/makin/src/node_workflow/.venv/bin/python`, and the separate
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

## Telegram launcher v0 (owner-requested, 2026-10-22)

One fixed saved workflow per command, using the existing JSON adapter. No
agent turn, plugin, argument passing or workflow creation. Hermes runs exec
quick commands after normal sender authorization; its top-level config is the
allowlist. The reply is stdout, otherwise stderr, with Hermes redaction.

The repository template `aotn-run-template.sh` is installed as
`aotn-run-<slug>.sh` under a real saved workflow slug, for example
`aotn-run-c1-notify-test.sh`. It derives the slug from its own filename (lowercase
letters, digits, `_` and `-`, beginning with a letter or digit), refuses arguments,
and uses these fixed paths:

- Checkout: `/home/makin/src/aotn-live`.
- Interpreter: `/home/makin/src/node_workflow/.venv/bin/python`.
- Data: `/home/makin/.local/share/aotn-cron`.

**Installation is a separate owner action**, after updating the live checkout.
The following example copies the adapter and only the requested named instance
into `$HERMES_HOME/scripts` (default `/home/makin/.hermes/scripts`). Both install
and check refuse directories, symlinks (including dangling links) and other
non-regular destinations. Installation uses a rename that cannot move a file
inside a directory. Content or mode drift is reported by `--check`; reinstall
restores entry scripts to 755 and shared files to 644. It does not
install other entry scripts, build the workflow, change config or start a job:

```bash
bash /home/makin/src/aotn-live/AttackOfTheNodes/integrations/hermes/install.sh --run-command c1-notify-test
bash /home/makin/src/aotn-live/AttackOfTheNodes/integrations/hermes/install.sh --check --run-command c1-notify-test
```

Then the owner may add this **example, not applied** to the top level of
`~/.hermes/config.yaml` (merge with existing quick commands):

```yaml
quick_commands:
  aotn_test:
    type: exec
    command: /home/makin/.hermes/scripts/aotn-run-c1-notify-test.sh
```

`/aotn_test` launches exactly that saved workflow. Text after the command is
not passed by Hermes; the script itself rejects any argv. Configure only
workflows the authorized sender should be able to run.

The `--telegram-launcher` adapter mode has a **25-second budget including
cleanup**, below Hermes's 30-second reply timeout (which does not kill scripts).
It reuses H0's process group, Linux subreaper, descendant kill/reap and persistent
lock marker. INT starts at 20 seconds; KILL at 24, reserving the final second
for reaping. Late external signals or pipe overflow do not extend that budget.
Other adapter calls retain H0's 100-second budget. A stop/timeout ends the run;
there is no background continuation or later reply. Cleanup failure leaves the
same stale lock marker requiring operator verification as H0.

V0 supplies an ISO UTC timestamp as `checked_at` only when the selected
workflow's Start contract declares that input. The CLI's opt-in
`--input-if-declared KEY=VALUE` resolves this against the same loaded Start
rows used for validation; the heartbeat still receives its timestamp. Callable
workflows without that row can launch using their saved defaults.
Other required Start inputs must have saved defaults, or the run is refused with
`Couldn't run <slug>: required inputs are missing or invalid; v0 supplies only checked_at`.
For example, a `sent_at` input without a default in `c1-notify-test` must be
configured before that workflow can be used here. Optional/defaulted inputs
use existing CLI behavior. Interactive prompts cannot be answered; the adapter
uses the existing unattended `terminate_workflow` policy.

Success returns the run's outputs and named results, with H0 escaping and a
3,500 UTF-16-unit cap including any truncation tail. An empty successful output
stays empty (Hermes then says “Command returned no output.”); completion
summaries and child diagnostics are not replies. Failure produces one plain
line, `Couldn't run <slug>: <reason>`, including a clear missing/unreadable
workflow message for an empty data directory; a timeout says
`Couldn't run <slug>: stopped after 25 s`. Full errors/outputs remain in run
history where a run started. The script does not install or update the live app.

`tests/test_telegram_launcher.py` exercises real subprocesses for entry naming,
argument refusal, a real 25-second deadline including a detached descendant's
reaping, timestamp/missing required inputs, escaping/cap, empty data/missing
workflows, and named install/check in a temporary Hermes folder. No live install
or Hermes configuration change is part of verification.

## Ask Hermes setup

Ask Hermes uses a separate Hermes profile through the public CLI. Set this up
before adding the node; AOTN does not create profiles or copy credentials.
The owner's existing profile is `~/.hermes/profiles/aotn`. It is an independent
`HERMES_HOME`, not the sticky default. Its CLI toolsets are disabled, MCP is
explicitly blocked, the resolver reports zero tools, memory is off, and it has
its own copied credentials. The default profile, gateway and cron jobs remain
separate.

Give Hermes the owner's setup prompt (replace nothing with secrets):

```text
With my approval, please set up an isolated profile for AttackOfTheNodes, without changing my default profile, gateway, cron jobs or memory:
1. Create a new profile named "aotn" (an independent HERMES_HOME). Don't make it the sticky default.
2. In that profile, disable every toolset and MCP tool for the CLI platform, so a chat there has no tools at all. Use the same model/provider credentials as my default profile.
3. Tell me exactly how to run one non-interactive question against that profile without changing the default (the env var or flag, e.g. HERMES_HOME=... or an alias wrapper), using: chat -q "<question>" -Q --source tool --max-turns 1.
4. Prove it: show tools list for that profile (nothing enabled), then run one test question in the profile asking you to run ls ~ and to read a file. Report whether any tool was used and what the reply was.
5. Confirm my default profile's tools, memory and cron jobs are unchanged.
```

Also confirm that the new profile's memory is off and MCP is explicitly blocked,
and have Hermes verify the resolved inventory is zero tools. Keep credentials
inside that profile, never in a workflow or AOTN Options. If copied credentials
expire, sign in for the **aotn profile**, not by adding a token to a node.

Verify the profile without making it the default. Each `HERMES_HOME` prefix
applies to that command only; do not export it for the AOTN app:

```bash
HERMES_HOME="$HOME/.hermes/profiles/aotn" "$HOME/.local/bin/hermes" tools list --platform cli
HERMES_HOME="$HOME/.hermes/profiles/aotn" "$HOME/.local/bin/hermes" chat -q "Reply with exactly: AOTN profile ready" -Q --source tool --max-turns 1 --ignore-rules
```

The listing must show **every toolset disabled**. AOTN checks before every
question, including repeated visits; enabled, unknown, duplicate or missing
rows and unclassified diagnostics all refuse the run. The current strict
format has 24 built-in CLI toolsets. A changed CLI listing requires parser
review, not silently trusting new output. There is no preflight cache.
The second command uses the profile's account and may incur usage; it should
return the answer only (`session_id` is metadata, normally on stderr).
`--source tool` is currently stored by Hermes as `cli`; this is harmless.

In AOTN Options, set **Hermes profile home** (`hermes_profile_home`, default
`~/.hermes/profiles/aotn`) and **Hermes command** (`hermes_command`, default
`~/.local/bin/hermes`). The explicit executable path works when cron's PATH
does not include `~/.local/bin`; it may be the owner's bash launcher wrapper.
Enable **Allow Ask Hermes without a dollar cap** only after accepting that
limit. Defaults do not enable paid runs automatically.

Add **Complex → AI Processing → Ask Hermes**. Choose Question from Configured,
Upstream payload or Vault, and an existing **Folder** allowed by Options
`system_node_folders`. The node runs that CLI command with an argv list, never
a shell command string, using the checked Folder as its working directory.
Question is one argument, limited to 20,000 characters. `--ignore-rules` prevents
Folder AGENTS.md, SOUL and other context files from loading. The configured
time limit covers tools preflight, chat startup, answer and process-tree cleanup;
Stop also kills and reaps detached descendants. Default 60 seconds, range 10–300.

This is **profile isolation, not an OS sandbox**. The CLI still runs as the
owner and manages its own profile sessions/authentication. Folder containment
checks authorize the starting directory; they do not create a filesystem or
network jail. Keep this profile dedicated and its permissions/configuration
under owner control. CLI/provider retries and billing behavior belong to Hermes;
`--max-turns 1` is a CLI limit, not proof of exactly one paid API request.
AOTN does not import Hermes internals, change its settings, enable tools, retry
failed questions, switch accounts, or change the default profile.

Missing profile: **Set up the aotn Hermes profile first**. Missing command:
**Hermes is not installed**. Unsafe or unclassifiable tools listing:
**This Hermes profile has tools turned on.** Expired login:
**Sign in to Hermes (aotn profile)**. Empty, malformed or oversized output is
`invalid_response`. Raw CLI diagnostics are never put into node errors or logs.
Answer is text; Run details is optional and Vault only. The standard forwarding
checkbox affects downstream only. `-Q` supplies no token/cost/turn measurements:
usage stays null/“not reported”, with the configured limit recorded separately.

[Run records, error contract and cleanup](../../docs/integrations/ASK_HERMES.md)
· [Built screens and smoke evidence](../../docs/audits/ask_hermes_2026_10_22/README.md).

## Investigation inbox (C3c, simple v1)

“Ask Hermes to investigate” queues an incident; “Investigation result” checks
its request id later. **AOTN gathers the evidence. Hermes has no tools and only
analyses the supplied excerpts.** This is report only: it cannot inspect paths,
run commands, browse, edit files or approve a repair. The separate read-only
evidence service from the design samples is deferred.

Owner setup, after reviewing and updating the live checkout (not performed by
this PR):

1. Complete [Ask Hermes setup](#ask-hermes-setup). Keep the tool-free `aotn`
   profile independent of the default; no memory, plugins/hooks, context files,
   fallback models or MCP tools. Its credentials are its own. This is profile
   isolation, not an OS sandbox. Every attempt strictly checks
   `tools list --platform cli`; enabled, missing, duplicate or unknown output
   refuses before chat. Do not enable tools for investigations.
2. In AOTN Options set **Investigations per day** (default 5; 0 turns new
   investigations off; maximum 50). **Investigation profile home** defaults to
   `~/.hermes/profiles/aotn`, and can point to another tool-free profile later.
   **Hermes command** is shared with Ask Hermes, default `~/.local/bin/hermes`.
   These are owner settings, never workflow parameters. A queued request
   publishes these three settings into the shared inbox policy. All writers
   for one shared inbox must use the same owner Options; the last enqueue
   refreshes that policy, including when the enqueue is a repeat/refused by cap.
3. Install/check the named entry, as copies (no symlinks):

   ```bash
   bash /home/makin/src/aotn-live/AttackOfTheNodes/integrations/hermes/install.sh --investigate-command home
   bash /home/makin/src/aotn-live/AttackOfTheNodes/integrations/hermes/install.sh --check --investigate-command home
   ```

   This copies `_aotn_investigate.py` and `aotn-investigate-home.sh` only. Wrong
   content/mode is drift; entry scripts are 755 and helpers 644. Directories,
   symlinks and other non-regular file destinations are refused. Entry names
   follow `aotn-investigate-<name>.sh`; arguments are refused. The suffix is a
   job label, not a queue partition: one shared investigation inbox, one worker.
4. Ask Hermes to create a **script-only** cron job every five minutes, using
   the installed script, `--no-agent`, and Telegram as its delivery target.
   Equivalent example, **not applied**:

   ```bash
   hermes cron create '*/5 * * * *' --name 'AOTN investigation inbox' --script aotn-investigate-home.sh --no-agent --deliver telegram
   ```

   Keep the job in the same scheduler home as the shared folder; do not use
   a per-job profile to relocate its scripts/inbox. The bridge independently
   selects the tool-free child profile. Verify the effective Hermes script
   timeout leaves at least 95 seconds: source default is 120 seconds, but a
   configured override may be shorter. No global timeout/config is changed by
   AOTN. Do not install a native agent job: `--no-agent` is essential to avoid
   an extra agent turn. When empty or another attempt owns the worker, stdout
   is exactly `{"wakeAgent": false}`. Otherwise stdout is the safe final report.

The installed entry uses `/home/makin/src/aotn-live`, the shared Python at
`/home/makin/src/node_workflow/.venv/bin/python`, and the separate data directory
`/home/makin/.local/share/aotn-cron`. Missing code/setup gives a plain line.
The inbox itself remains `$HERMES_HOME/aotn/investigations`, **not** inside the
child profile. No Hermes configuration, job or live install is applied here.

### Workflow and limits

Use What happened plus optional Short excerpts from Upstream payload, Vault or
Configured. Each has its own standard source selector. Gather logs/check results
with existing nodes first; a path in an excerpt is just text and is never opened
by this feature. What to check is configured text. Known Secrets-store values,
labelled credentials, bearer tokens, URL passwords and private-key blocks are
redacted before request persistence; use secret references rather than typing
credentials into saved parameters. Unknown secrets cannot be inferred reliably;
keep evidence deliberately small. No raw CLI diagnostics are saved or printed.
The bridge also redacts its own Secrets-store values before saving findings.

Bounds: 4,000 characters each for What happened and What to check, 8,000 for
excerpts, 20,000 for the complete untrusted-evidence envelope, 128 KiB per JSON
record. Oversize input is refused rather than silently truncating the task.
When accepts a timestamp with time zone; blank means now. No project Folder
setting/evidence access is needed: the child works in the private inbox with
`--ignore-rules`, one turn and `--query=<envelope>` as **one argv element**.

One attempt at a time, oldest first. The **90-second total attempt budget**
includes tool preflight/chat/whole-process-tree cleanup, with time reserved for
result publication; SIGTERM/SIGINT (Stop) cancels the attempt. Linux subreapers
reap detached descendants too. No automatic paid retries. Starts and accepted
new requests each have the same per-UTC-day cap across workflows. An uncertain
start stays charged; failures/tool refusals also consume their start reservation.
Requests already queued wait if today's start cap is used. Cap zero pauses
starts; the new request call can still return an existing id for a repeat.

The cap counts attempts, **not dollars**. The one-turn CLI does not report
reliable token/cost/turn telemetry; result usage is null/“not reported”. Actual
charges remain visible in the owner's Hermes account/provider billing. The
Ask Hermes dollar-cap opt-in applies to its node, not this separately capped,
owner-enabled cron inbox. No claimed currency budget or invented estimate.

Repeat key/window match C1 semantics: blank key is run/node/branch, 0 disables,
up to 1,440 minutes, future timestamps do not suppress. Use a stable explicit
key for the same incident across runs. A repeat returns the original request
id and consumes no new quota. C1 `repeats.json` is unchanged.

Save Request id with Remember for a later run; the Vault alone is per-run.
Investigation result returns Finding or plain `not ready yet` / `failed`; its
optional Vault-only State is `ready`, `not ready yet`, or `failed`. Compare State
in Conditional, then have Notify me read Finding from the Vault (Conditional
forwards the compared state). Standard forwarding affects downstream only;
enabled Vault rows retain the node's own values. There is no polling loop or
new trigger node. Cron already sends its final reply to Telegram: a later
Notify me is an optional follow-up, not a second automatic report.

A request left working for five minutes is failed, never automatically retried.
A never-launched attempt or a prior boot can be reconciled safely. An ambiguous
same-boot launch leaves `cleanup-required.json` and blocks further starts;
AOTN does not guess ownership from a reusable PID. The owner must confirm the
old bridge and descendants have stopped, inspect the failed/working records,
and only then remove that marker. Missing/malformed leases also block. A valid
result published before a crash wins; recovery completes its folder move without
another inference or automatic repeat Telegram delivery.

Reports escape H0 control directives and cap stdout at 3,500 UTF-16 units; full
finding (up to 12,000 characters) stays in the result file. Telegram delivery is
a handoff, not a confirmed receipt: `handoff_unknown` is deliberate. Results and
quota/request files are retained in v1; no automatic pruning. Do not delete or
move today's accounting/request records to bypass a cap. See the versioned
[record contract](../../docs/integrations/HERMES_SHARED_FOLDER.md#investigation-inbox-c3c).
