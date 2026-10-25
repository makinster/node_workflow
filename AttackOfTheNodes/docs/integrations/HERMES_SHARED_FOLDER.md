# Hermes shared folder

AOTN owns these formats (AI coordination decision C2). Hermes, the outbox
drain and anything else that reads the folder follow this page. Every line
carries `schema_version`; a reader skips or sets aside versions it does not
know. Built in C1 (owner approved the samples on 2026-10-21).

## The folder

`$HERMES_HOME/aotn/`, with `HERMES_HOME` defaulting to `~/.hermes`: the one
setting both the nodes and the drain read (#109 review; an Options value could
point the nodes at a folder the drain never reads). The path never comes from
a workflow, so Notify me and Record event do not use the System nodes' allowed
folders (owner, 2026-10-21).

Rules every writer follows (the nodes and the drain alike):

- The folder is the owner's only (700) and every file in it (600), set on each
  change, including folders and files that already existed with looser modes.
  A symbolic link in their place is refused.
- Every change holds the folder's `.lock` (`flock`).
- Lines end with LF only. A line with no LF after it was left by a writer that
  died mid-line: before appending, the writer moves it to
  `<file>.bad.jsonl` and cuts it off, so the next line starts clean.

| File | Written by | Read by | Purpose |
|---|---|---|---|
| `outbox.jsonl` | Notify me (adds), drain (removes) | drain | Messages waiting to send |
| `events.jsonl` | Notify me, Record event, drain | Hermes, digest workflows | History, only ever appended to |
| `repeats.json` | Notify me, Record event | the same nodes | When each repeat key last went out (a day at most; times in the future count as expired) |
| `outbox.bad.jsonl`, `events.bad.jsonl` | drain, nodes | the owner | Lines that could not be read, or were left unfinished |

A repeat is remembered only after its record is written, so a failed write
never makes a retry look like a repeat. The outbox line is the record that
counts: once it is written the message is queued, even if its `queued`
history line then fails.

## outbox.jsonl

One JSON object per line, one line per message.

| Field | Example | Meaning |
|---|---|---|
| `schema_version` | `1` | |
| `receipt_id` | `"r_20261021_210411_a3f9c1"` | Ties the message to its receipts |
| `created_at` | `"2026-10-21T21:04:11Z"` | UTC |
| `workflow`, `run_id`, `node_id`, `branch` | `"Nightly backup"`, … | Where it came from |
| `send_to` | `"home"` | A name in Options (`hermes_send_to_names`), set up in Hermes as a drain job. Never a chat id |
| `priority` | `"normal"` or `"urgent"` | Urgent goes first in the digest, marked ⚠ |
| `repeat_key` | `"run_1/node_1/S1"` | Run + node + branch unless the node sets its own |
| `hermes_commands` | `false` | `true` only when Allow Hermes commands is on |
| `message` | `"Backup done. 41.2 GB free"` | Already escaped (unless `hermes_commands`) and cut to the node's Longest message (at most 3,500) |

## events.jsonl

Two kinds of line. Readers that print anything from here must escape it
(the same rule as the H0 adapter).

**receipt**: one line per stage of a message.

| Field | Meaning |
|---|---|
| `schema_version`, `event_id`, `kind: "receipt"`, `receipt_id` | |
| `stage` | `queued` (Notify me), `skipped` (a repeat; never queued), `handed_off` (printed by the drain), `delivered` / `failed` (later, see below) |
| `stage_at` | UTC |
| `by` | `node`, `drain` or `reconciler` |
| `workflow`, `run_id`, `node_id`, `branch` | As in the outbox |

**event**: one line per Record event.

| Field | Meaning |
|---|---|
| `schema_version`, `event_id`, `kind: "event"`, `created_at` | |
| `name` | A short name such as `backup.done` |
| `summary` | One line, escaped, at most 300 characters |
| `value` | The incoming value as escaped text (at most 2,000 characters) when Also keep is on; otherwise `null` |
| `workflow`, `run_id`, `node_id`, `branch` | Where it came from |

## The outbox drain

`integrations/hermes/aotn-drain-<name>.sh` runs `_aotn_drain.py` as a
no-agent Hermes cron job, every 5 minutes, one job per Send to name (C3: one
digest per tick). Each tick, holding the lock:

1. Make the folder and its files the owner's only. Read the outbox line by
   line (LF only: a message may contain U+2028 or U+0085). Unreadable or
   unfinished lines, and lines of another `schema_version`, move to
   `outbox.bad.jsonl` and are counted in the digest.
2. Take this name's messages, urgent first, then oldest first. A message with
   `hermes_commands` goes out **alone** when it is first in line: Hermes applies
   a command such as `[SILENT]` to the whole reply, so it must never share one
   with other nodes' messages. The others go into one digest of at most 3,500
   UTF-16 units, counting the header, separators, notes and final newline;
   what does not fit waits ("+N more next time"), and a single message too long
   to fit is cut by the same count.
3. Print it, escaping again any message without `hermes_commands`.
   Nothing waiting: print nothing, so Hermes sends nothing.
4. After printing, add a `handed_off` receipt per message and rewrite the
   outbox without them.

Exit 0 (printed, or nothing to send), 64 usage, 70 failure (Hermes alerts;
the queue stays), 75 folder busy. A crash between printing and step 4
resends those messages next tick: at least once, never lost.

## Sound

Hermes (installed version, checked 2026-10-21) has no per-job or output
option for silent delivery. Through the running gateway, cron deliveries are
already silent (its Telegram adapter only rings when a message asks to
notify, which cron never does), so **Urgent does not ring either**: it only
goes first with ⚠. Hermes's standalone fallback delivery path does ring.
Per-job sound control would need a Hermes change; that is a follow-up, and
nothing here depends on it.

## Not yet

- `delivered` / `failed` receipts need a reconciler that reads Hermes's
  delivery records (proposal Q2).
- `memory_proposals.jsonl` (proposal section 5.4) comes with the propose node.

## Investigation inbox (C3c)

Simple v1, owner decision 2026-10-23: AOTN supplies short excerpts; the Hermes
investigator has **no tools**, one turn, report only. Evidence paths are inert
text. No read-only evidence service, terminal, web, file or MCP access is added.
Setup and the unapplied cron example are in the
[adapter guide](../../integrations/hermes/README.md#investigation-inbox-c3c-simple-v1).

Under the same shared root (not the investigator's `HERMES_HOME`):

```text
.lock                                  existing C1 mutation flock
investigations/                         directories 700, regular files 600
  policy.json                          owner Options, refreshed on enqueue
  worker.lock                          one complete attempt, nonblocking flock
  pending/<request-id>.json             immutable requests
  working/<request-id>.json             oldest claim, atomic rename
  done/<request-id>.json                request after ready result
  failed/<request-id>.json              request after failed result
  results/<request-id>.json             atomic terminal finding/failure
  leases/<request-id>.json              attempt ownership/phase, removed on finish
  attempts/<attempt-id>.json            durable start reservations, retained
  cleanup-required.json                only on unconfirmed cleanup; blocks starts
```

All JSON records have integer `schema_version: 1`; unknown/malformed versions
refuse rather than silently resetting quotas. Regular-file/no-symlink checks,
bounded reads, private modes, same-filesystem temporary writes, file fsync,
exact atomic rename and directory fsync protect publication. The shared `.lock`
protects short transitions (two-second lock wait); no lock is held across
inference except the independent worker lock. Request ids match
`i_YYYYMMDD_HHMMSS_<32 lowercase hex>` and cannot be arbitrary filenames.

Request example (synthetic id):

```json
{
  "schema_version": 1,
  "request_id": "i_20261023_101400_8d4ae0d12cd840f3891cc7e46ac6409b",
  "queued_at": "2026-10-23T10:14:00Z",
  "incident_at": "2026-10-23T10:14:00Z",
  "mode": "report_only",
  "what_happened": "The service returned HTTP 503 four times.",
  "evidence": "10:14 UTC: database connection failed; password=[redacted]",
  "what_to_check": "Find a likely cause; suggest next checks without changes.",
  "repeat_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "repeat_minutes": 60,
  "origin": {"workflow": "Service check", "run_id": "run_1", "node_id": "ask", "branch": "main"}
}
```

Repeat digests are SHA-256 of the explicit key or C1 run/node/branch default;
raw repeat keys are not saved. Canonical request files across the four stage
folders determine repeats and today's admissions. Repeats return the same id;
no second index or mutation of C1 `repeats.json`. Future timestamps expire for
repeat suppression. Stored request timestamps have zones. Inputs are redacted
before writing, not left for Hermes to sanitize. Limits: description/task 4,000
characters each, excerpts 8,000, whole prompt 20,000, each record 128 KiB.

The shared redactor also masks multiline credential values: literal/folded
YAML blocks, indented values after a credential key and unindented continuation
blocks (the value may also start inline after the label). Indented blocks
end at dedent; unindented blocks end at a blank line or
next field. PEM/private-key blocks are removed, including incomplete blocks.
URL userinfo is masked for any scheme case/name (`HTTPS`, `ftp`, `ssh`, etc.),
including username-only URLs. This same helper protects MCP activity findings
and event summaries before caps and worker output.

Policy shape:

```json
{"schema_version":1,"daily_limit":5,"profile":"/home/makin/.hermes/profiles/aotn","command":"/home/makin/.local/bin/hermes"}
```

`hermes_investigations_per_day` (0–50, default 5),
`hermes_investigation_profile_home` (default `~/.hermes/profiles/aotn`) and shared
`hermes_command` come only from owner Options. All apps using one inbox must
agree on these settings; last enqueue publishes them. Both admission count and
start count are limited independently per UTC day; this is not a dollar limit.
No silent quota reset on bad records; retained files are the accounting source.
Pending capacity is 100. No automatic record deletion/retention sweep in v1.

A start reservation is written before spawning:

```json
{"schema_version":1,"attempt_id":"a_0123456789abcdef0123456789abcdef","request_id":"i_20261023_101400_8d4ae0d12cd840f3891cc7e46ac6409b","at":"2026-10-23T10:15:00Z"}
```

Lease fields: `schema_version`, `request_id`, `attempt_id`, `claimed_at` (UTC),
`claimed_epoch` (seconds), `boot_id`, `owner_pid` (diagnostic only),
`phase` (`claimed`, `launching`, `finished`), `cleanup_confirmed` (boolean).
The bridge persists `launching`/false **before** any spawn. A stale lease after
300 seconds is never a paid retry: safe never-launched/prior-boot work becomes
failed `interrupted`; ambiguous same-boot work becomes `cleanup_failed` and
blocks new starts. Missing/malformed ownership also blocks. The marker shape is
`schema_version`, `request_id`, `code: cleanup_failed`, safe `message`, and `at`.
Only an owner who has confirmed cleanup should remove it; PID existence alone
cannot prove detached descendants stopped.

Terminal result fields:

| Field | Meaning |
|---|---|
| `schema_version`, `request_id`, `attempt_id` | Version and correlation |
| `state` | `ready` or `failed` |
| `finding` | Redacted nonempty text for ready (at most 12,000 characters), empty for failed |
| `failure` | null for ready; `{code, message}` for failed; no raw stderr |
| `started_at`, `finished_at` | UTC timestamps |
| `mode`, `tools` | `report_only`, `[]` |
| `limits` | `{seconds: 90, turns: 1, budget_usd: null}` |
| `usage` | `cost_status: not_reported`, null `estimated_cost_usd`, `input_tokens`, `output_tokens` |
| `cleanup_confirmed` | true only after process-tree cleanup is established |
| `notification` | `handoff_unknown`; stdout is not proof of delivery |

Investigation JSON is UTF-8 without ASCII expansion, so supplementary Unicode
characters do not consume twelve serialized bytes each. Lone surrogates use the
same UTF-8 replacement as C1 escaping; U+2028/U+0085 remain data rather than LF
framing in the stored finding. CLI session framing is LF-only, with embedded
receipts still refused. If a serialized finding exceeds the record budget,
publish a terminal `invalid_response` failure immediately. The final stdout
cap includes the entry's newline as well as every header and truncation mark.

Write the result atomically before moving working to done/failed; a published
valid result is authoritative if a crash interrupts that last rename. Recovery
finishes the move without inference or duplicate automatic delivery. No terminal
result overwrite or request-id mismatch. Result reader returns the finding and
State `ready`, otherwise literal `not ready yet` for pending/working or `failed`
for a terminal failure. State is an optional string Vault output for Conditional;
Finding follows standard downstream/Vault forwarding. Unknown id, corrupt record,
wrong version and unreadable inbox are node errors, not invented pending states.

Worker failure codes reuse #116: `profile_missing`, `not_installed`,
`permission_denied` (any enabled/unknown tools), `auth_failed`, `invalid_response`,
`agent_failed`, `timed_out`, `cleanup_failed`, plus `cancelled` and `interrupted`.
All failures consume their start reservation; no automatic retry. Empty/locked/
start-capped inbox emits exactly `{"wakeAgent": false}`; infrastructure/cleanup
problems emit a plain safe line without waking an extra agent. Nonempty reports
use H0 escaping and a 3,500 UTF-16-unit cap. A script-only cron job prints that
report directly; it does not use a native agent-job precheck/context hook.
