#!/bin/sh
set -eu
app_password=$(cat /run/sentinel/app-db.password)
grafana_password=$(cat /run/sentinel/grafana-db.password)
test -n "$app_password"
test -n "$grafana_password"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_password="$app_password" \
  --set=grafana_password="$grafana_password" <<'SQL'
CREATE ROLE sentinel_app LOGIN PASSWORD :'app_password';
CREATE ROLE grafana_reader LOGIN PASSWORD :'grafana_password';
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE TABLE observations (
    id BIGSERIAL PRIMARY KEY, kind TEXT NOT NULL, device TEXT NOT NULL,
    message_id TEXT NOT NULL, received_at DOUBLE PRECISION NOT NULL,
    payload JSONB NOT NULL, UNIQUE(kind, device, message_id)
);
CREATE INDEX observations_kind_time ON observations(kind, received_at);
CREATE TABLE security_events (
    id BIGSERIAL PRIMARY KEY, received_at DOUBLE PRECISION NOT NULL,
    reason TEXT NOT NULL, transport TEXT NOT NULL
);
CREATE INDEX security_events_time ON security_events(received_at);
GRANT CONNECT ON DATABASE sentinel TO sentinel_app, grafana_reader;
GRANT USAGE ON SCHEMA public TO sentinel_app, grafana_reader;
GRANT SELECT, INSERT ON observations, security_events TO sentinel_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sentinel_app;
GRANT SELECT ON observations, security_events TO grafana_reader;
ALTER ROLE grafana_reader SET default_transaction_read_only = on;
ALTER ROLE grafana_reader SET statement_timeout = '10s';
SQL
