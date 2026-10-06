#!/bin/sh
set -eu
export SENTINEL_PG_PASSWORD="$(cat /run/sentinel/grafana-db.password)"
exec /run.sh
