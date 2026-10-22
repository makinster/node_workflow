#!/usr/bin/env bash
# Template: install as aotn-run-<saved-workflow-slug>.sh using --run-command.
# Fixed production paths; no arguments, environment timing or workflow override.
entry_name=${BASH_SOURCE[0]##*/}
if [[ ! $entry_name =~ ^aotn-run-([a-z0-9][a-z0-9_-]*)\.sh$ ]]; then
    printf '%s\n' "Couldn't run workflow: name this script aotn-run-<slug>.sh."
    exit 64
fi
slug=${BASH_REMATCH[1]}
if [[ $# -ne 0 ]]; then
    printf "Couldn't run %s: arguments are not supported.\n" "$slug"
    exit 64
fi
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P) || {
    printf "Couldn't run %s: launcher folder is unavailable.\n" "$slug"
    exit 70
}
python=/home/makin/src/node_workflow/.venv/bin/python
if [[ ! -x $python || ! -r $script_dir/_aotn_run.py ]]; then
    printf "Couldn't run %s: launcher installation is incomplete.\n" "$slug"
    exit 70
fi
exec "$python" "$script_dir/_aotn_run.py" --telegram-launcher \
    --workflow-slug "$slug" --project-root /home/makin/src/aotn-live \
    --data-dir /home/makin/.local/share/aotn-cron --python "$python"
