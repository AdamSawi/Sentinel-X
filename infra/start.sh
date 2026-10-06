#!/bin/sh
set -eu
umask 027
if [ ! -f /run/sentinel/server.crt ]; then
  openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
    -keyout /run/sentinel/server.key -out /run/sentinel/server.crt \
    -subj '/CN=localhost' \
    -addext 'subjectAltName=DNS:localhost,DNS:mqtt,IP:127.0.0.1' \
    -addext 'extendedKeyUsage=serverAuth' >/dev/null 2>&1
fi
for account in backend sensors vision; do
  if [ ! -f "/run/sentinel/$account.password" ]; then
    openssl rand -hex 24 > "/run/sentinel/$account.password"
  fi
  if [ ! -f /run/sentinel/passwords ]; then
    mosquitto_passwd -b -c /run/sentinel/passwords "$account" "$(cat "/run/sentinel/$account.password")"
  else
    mosquitto_passwd -b /run/sentinel/passwords "$account" "$(cat "/run/sentinel/$account.password")"
  fi
done
chown -R mosquitto:mosquitto /run/sentinel /mosquitto/data
chmod 750 /run/sentinel
chmod 640 /run/sentinel/*
chmod 600 /run/sentinel/server.key /run/sentinel/passwords
exec mosquitto -c /mosquitto/config/mosquitto.conf
