#!/usr/bin/env bash
set -euo pipefail
source "${HERMES_HOME:-/home/makin/.hermes}/scripts/_aotn_common.sh"
aotn_cron_run "$0" "$@"
