#!/usr/bin/env bash
# Hermes no-agent job: one digest of queued AOTN messages for the Send to
# name in this file's name (aotn-drain-<name>.sh). Copy it to add a name.
# The folder is $HERMES_HOME/aotn (HERMES_HOME defaults to ~/.hermes), the
# same rule Notify me and Record event follow (backend/hermes_folder.py).
entry_name=${BASH_SOURCE[0]##*/}
if [[ $# -ne 0 || ! $entry_name =~ ^aotn-drain-([a-z0-9][a-z0-9_-]*)\.sh$ ]]; then
    printf '%s\n' 'Outbox drain takes no arguments; name it aotn-drain-<name>.sh.' >&2
    exit 70
fi
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P) || exit 70
exec /home/makin/src/node_workflow/.venv/bin/python "$script_dir/_aotn_drain.py" \
    --send-to "${BASH_REMATCH[1]}" --folder "${HERMES_HOME:-$HOME/.hermes}/aotn"
