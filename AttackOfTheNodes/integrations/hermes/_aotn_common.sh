#!/usr/bin/env bash
# Source from aotn-<saved-workflow-name>.sh; installation is an owner action.
aotn_cron_run() {
    if [[ $# -ne 1 ]]; then
        printf '%s\n' 'AOTN wrapper accepts only its entry filename, no arguments.' >&2
        return 70
    fi
    local entry_name=${1##*/}
    if [[ ! $entry_name =~ ^aotn-([a-z0-9][a-z0-9_-]*)\.sh$ ]]; then
        printf '%s\n' 'AOTN wrapper requires filename aotn-<slug>.sh.' >&2
        return 70
    fi
    local slug=${BASH_REMATCH[1]}
    local root=/home/makin/src/node_workflow
    local python=/home/makin/src/node_workflow/.venv/bin/python
    local data=/home/makin/.local/share/aotn-cron
    # Resolve relative to this sourced file, so linked/copied deployments work.
    local common_file=${BASH_SOURCE[0]}
    local adapter_dir
    adapter_dir=$(cd -- "$(dirname -- "$common_file")" && pwd -P) || return 70
    cd -- "$root" || return 70
    local -a argv=("$python" "$adapter_dir/_aotn_run.py"
        --workflow-slug "$slug" --project-root "$root" --data-dir "$data" --python "$python")
    exec "${argv[@]}"
}
