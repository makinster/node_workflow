#!/usr/bin/env bash
# Copy as aotn-investigate-<name>.sh for a Hermes --no-agent cron job.
entry_name=${BASH_SOURCE[0]##*/}
if [[ $# -ne 0 || ! $entry_name =~ ^aotn-investigate-([a-z0-9][a-z0-9_-]*)\.sh$ ]]; then
    printf '%s\n' 'Investigation bridge takes no arguments; name it aotn-investigate-<name>.sh.'
    exit 64
fi
name=${BASH_REMATCH[1]}
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P) || exit 70
python=/home/makin/src/node_workflow/.venv/bin/python
if [[ ! -x $python || ! -r $script_dir/_aotn_investigate.py ]]; then
    printf '%s\n' 'Investigation bridge installation is incomplete.'
    exit 70
fi
exec "$python" "$script_dir/_aotn_investigate.py" --name "$name" \
    --project-root /home/makin/src/aotn-live --data-dir /home/makin/.local/share/aotn-cron \
    --folder "${HERMES_HOME:-$HOME/.hermes}/aotn"
