# Hermes shared folder

AOTN owns these formats (AI coordination decision C2). Hermes, the outbox
drain and anything else that reads the folder follow this page. Every line
carries `schema_version`; a reader skips or sets aside versions it does not
know. Built in C1 (owner approved the samples on 2026-10-21).

## The folder

`~/.hermes/aotn/` by default (Options: `hermes_folder`). The folder is the
owner's only (700) and so is every file (600). The path comes from Options,
never from a workflow, so Notify me and Record event do not use the System
nodes' allowed folders (owner, 2026-10-21). Writers and the drain take the
folder's `.lock` (`flock`) for every change.

| File | Written by | Read by | Purpose |
|---|---|---|---|
| `outbox.jsonl` | Notify me (adds), drain (removes) | drain | Messages waiting to send |
| `events.jsonl` | Notify me, Record event, drain | Hermes, digest workflows | History, only ever appended to |
| `repeats.json` | Notify me, Record event | the same nodes | When each repeat key last went out (a day at most) |
| `outbox.bad.jsonl` | drain | the owner | Outbox lines the drain could not read |

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

1. Read the outbox. Unreadable lines, and lines of another
   `schema_version`, move to `outbox.bad.jsonl` and are counted in the
   digest.
2. Take this name's messages, urgent first, then oldest first, into one
   digest of at most 3,500 characters. What does not fit waits ("+N more next
   time").
3. Print the digest, escaping again any message without `hermes_commands`.
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
