# Why AttackOfTheNodes exists

AttackOfTheNodes is a workflow tool for complicated jobs that take time.
The goal is to make long runs predictable: build a recipe, see what is happening,
supply input, recover from a failure and understand what actually ran. A large
node catalog is useful only when those nodes can be composed with confidence.

The factory-and-control-room model keeps that purpose clear. Nodes are small
machines, the backend runs the factory floor, and the interface lets a person
arrange and observe the work. Execution should not depend on which interface
started it. The terminal app and CLI already share the backend; additional
clients belong on that same foundation.

## Contracts people can trust

A node should declare its inputs, outputs, types, requirements and effects once.
The selector, configuration form, connection chooser, validator and runtime
should tell the same story. A green check should mean that the configured
behavior is the behavior the engine will honor. That is a direction to work
toward, not a claim that preflight proves every runtime value today.

Small, single-purpose nodes and a dependable authoring helper make community
extensions practical. Different port shapes deserve different types; small
configuration differences usually deserve a mode. The helper should remove
routine work without concealing custom behavior or pretending regeneration is
lossless. [Node Standards](NODE_STANDARDS.md) owns that contract.

## Workflows beyond one terminal session

The [distributed plan](DISTRIBUTED_BUILD_PLAN.md) calls for a common Start/End
contract for every caller. A reusable subworkflow becomes a separate child run,
with its own memory, identity and resource lifetime, linked to its parent.
Triggers launch finite runs with explicit queue/drop behavior; they do not keep
one watcher workflow alive forever. These decisions preserve understandable
cleanup and make “call and wait” and “fire and forget” variations of one model.
Child-run execution, triggers and the server remain planned capabilities; the
run-context foundation does not establish concurrent-run isolation by itself.

The [Stash](STASH_PROPOSAL.md) addresses a daily obstacle: repeatedly entering
paths and reusable text. It keeps machine-local values outside a portable
workflow. Its core storage and CLI provide the first step; field insertion and
contract-input bindings extend that idea in stages. It is separate from the
per-run Vault and from secrets. Moving a workflow to another machine should
mean deliberately rebinding its inputs, not finding hidden paths in every node.
See [Current State](CURRENT_STATE.md) for delivery and approval status.

## Honest recovery and inspection

A handled error should remain visible without making successful recovery look
like failure. A stopped or skipped visit must not become a checkmark. Repeated
visits and retries need distinct identities. Future branch inspection should
preserve the user's place and show bounded, correctly attributed previews;
it must not guess old values from shared memory.

Files, histories and handles need explicit owners and predictable cleanup.
Failure evidence should remain available when a run does not succeed. These
principles do not promise general checkpointing or crash-resume support.
[Architecture](ARCHITECTURE.md) describes what the engine actually guarantees.

## A plain control room

The interface should stay compact, keyboard-first and clear. Names, source/type
previews, applicable controls and Save/Discard/Stay choices should help someone
reason about a graph. Live output panels and reusable node libraries serve that
purpose; decoration is not a substitute for truthful state.

Windows, macOS and Linux support is an ambition requiring capability detection
and native verification. WSL is a development environment, not evidence that
all desktop integrations work. Keep portable behavior shared, isolate platform
operations, and explain unavailable capabilities. Future work and its rationale
remain in [Project Backlog](PROJECT_BACKLOG.md).
