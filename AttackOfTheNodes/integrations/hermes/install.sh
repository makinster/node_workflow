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
if [[ $# -gt 1 || ( $# -eq 1 && $1 != --check ) ]]; then
    printf '%s\n' 'usage: install.sh [--check]' >&2
    exit 64
fi
[[ $# -eq 1 ]] && check=true

source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
target_dir=${HERMES_HOME:-/home/makin/.hermes}/scripts
files=(_aotn_common.sh _aotn_run.py aotn-h1-heartbeat.sh aotn-h2-http-watchdog.sh)

differs=0
for name in "${files[@]}"; do
    target=$target_dir/$name
    if [[ -L $target ]]; then
        printf 'refusing: %s is a symlink (Hermes rejects those); remove it first\n' "$target" >&2
        exit 70
    fi
    if [[ -f $target ]] && cmp -s -- "$source_dir/$name" "$target"; then
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
    cp -- "$source_dir/$name" "$temp"
    chmod "$mode" -- "$temp"
    mv -f -- "$temp" "$target"
    printf 'installed   %s\n' "$name"
done
if $check; then
    exit "$differs"
fi
