#!/usr/bin/env bash
# Copy the H0 wrapper files into Hermes's scripts folder (owner action).
#
# Hermes rejects scripts whose real path is outside $HERMES_HOME/scripts, so
# these are copies, not symlinks. Rerun after updating the live checkout:
#   bash /home/makin/src/aotn-live/AttackOfTheNodes/integrations/hermes/install.sh
# --check reports whether the installed copies match this checkout, changing
# nothing (exit 1 when they differ or are missing).
set -euo pipefail

check=false
run_slug=
while [[ $# -gt 0 ]]; do
    case $1 in
        --check) check=true; shift ;;
        --run-command)
            if [[ $# -lt 2 || -n $run_slug || ! $2 =~ ^[a-z0-9][a-z0-9_-]*$ ]]; then
                printf '%s\n' 'usage: install.sh [--check] [--run-command <slug>]' >&2
                exit 64
            fi
            run_slug=$2
            shift 2 ;;
        *) printf '%s\n' 'usage: install.sh [--check] [--run-command <slug>]' >&2
           exit 64 ;;
    esac
done

source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
target_dir=${HERMES_HOME:-/home/makin/.hermes}/scripts
files=(_aotn_common.sh _aotn_run.py aotn-h1-heartbeat.sh aotn-h2-http-watchdog.sh
       _aotn_drain.py aotn-drain-home.sh)
# Named launcher installation changes only the adapter and requested instance.
if [[ -n $run_slug ]]; then
    files=(_aotn_run.py "aotn-run-$run_slug.sh")
fi

differs=0
for name in "${files[@]}"; do
    target=$target_dir/$name
    source=$source_dir/$name
    [[ $name == "aotn-run-$run_slug.sh" ]] && source="$source_dir/aotn-run-template.sh"
    if [[ -L $target ]]; then
        printf 'refusing: %s is a symlink (Hermes rejects those); remove it first\n' "$target" >&2
        exit 70
    fi
    if [[ -f $target ]] && cmp -s -- "$source" "$target"; then
        printf 'up to date  %s\n' "$name"
        continue
    fi
    differs=1
    if $check; then
        printf '%-11s %s\n' "$([[ -f $target ]] && echo differs || echo missing)" "$name"
        continue
    fi
    mkdir -p -- "$target_dir"
    mode=644
    [[ $name == aotn-*.sh ]] && mode=755
    temp=$(mktemp -- "$target_dir/.$name.XXXXXX")
    cp -- "$source" "$temp"
    chmod "$mode" -- "$temp"
    mv -f -- "$temp" "$target"
    printf 'installed   %s\n' "$name"
done
if $check; then
    exit "$differs"
fi
