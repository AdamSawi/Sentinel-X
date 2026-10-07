#!/usr/bin/env bash
# Sentinel-X - Tests de sécurité automatisés (environnement local autorisé uniquement)
# Usage : depuis le dossier Sentinel-X, lancer :  bash cybersecurite/tests-cyber.sh
set -u
cd "$(dirname "$0")/.." || exit 1
exec </dev/null

DC="docker compose"
API="http://localhost:8080"
VISION="http://localhost:8090"
GRAFANA="http://localhost:3000"
RUN_ID="cyber-$(date +%s)"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OUT="cybersecurite/resultats-tests-$(date +%Y%m%d-%H%M).txt"
PASS=0
FAIL=0

exec > >(tee "$OUT") 2>&1

ok()   { echo "  [OK]    $1"; PASS=$((PASS+1)); }
ko()   { echo "  [ECHEC] $1"; FAIL=$((FAIL+1)); }
check() { # check "description" "attendu" "obtenu"
  if [ "$2" = "$3" ]; then ok "$1 (attendu $2, obtenu $3)"; else ko "$1 (attendu $2, obtenu $3)"; fi
}
http() { curl -s -o /dev/null -w "%{http_code}" "$@"; }
secret() { $DC exec -T mqtt cat "/run/sentinel/$1.password" | tr -d '\r\n'; }
mqtt_pub() { timeout -k 5 15 $DC exec -T mqtt mosquitto_pub -h localhost -p 8883 "$@" >/dev/null 2>&1; echo $?; }
port_open() { timeout 3 bash -c "</dev/tcp/$1/$2" 2>/dev/null && echo ouvert || echo ferme; }
event() { # event device message_id
  printf '{"device_id":"%s","message_id":"%s","observed_at":"%s","simulated":true,"event_type":"heartbeat","zone":"test-cyber","description":"test securite"}' "$1" "$2" "$NOW"
}
telemetry() { # telemetry message_id temperature
  printf '{"device_id":"test-cyber","message_id":"%s","observed_at":"%s","simulated":true,"temperature_c":%s}' "$1" "$NOW" "$2"
}
stored() { curl -s "$API/api/events?limit=1000" | grep -q "\"$1\"" && echo present || echo absent; }

echo "=== Tests de sécurité Sentinel-X - $(date '+%d/%m/%Y %H:%M:%S') - run $RUN_ID ==="
SENSORS=$(secret sensors)
VISIONPW=$(secret vision)
GRAFANADB=$(secret grafana-db)
if [ -z "$SENSORS" ] || [ -z "$VISIONPW" ]; then
  echo "Impossible de lire les secrets : lancer le script depuis le dossier Sentinel-X, stack démarrée."; exit 1
fi

echo; echo "1. MQTT : chiffrement et authentification"
CA="--cafile /run/sentinel/server.crt"
[ "$(mqtt_pub $CA -t sentinel/test -m x)" != 0 ] && ok "Connexion anonyme refusée" || ko "Connexion anonyme acceptée"
[ "$(mqtt_pub $CA -u sensors -P mauvais-mot-de-passe -t sentinel/test -m x)" != 0 ] && ok "Mauvais mot de passe refusé" || ko "Mauvais mot de passe accepté"
[ "$(mqtt_pub -u sensors -P "$SENSORS" -t sentinel/test -m x)" != 0 ] && ok "Connexion sans TLS refusée sur 8883" || ko "Connexion sans TLS acceptée"
[ "$(timeout -k 5 15 $DC exec -T mqtt mosquitto_pub -h localhost -p 1883 -u sensors -P "$SENSORS" -t sentinel/test -m x >/dev/null 2>&1; echo $?)" != 0 ] \
  && ok "Aucun port MQTT en clair (1883)" || ko "Port MQTT en clair actif (1883)"

echo; echo "2. MQTT : droits par compte (ACL)"
ID_BLOCK="$RUN_ID-acl-bloque"; ID_OK="$RUN_ID-acl-ok"
mqtt_pub $CA -V mqttv5 -q 1 -u sensors -P "$SENSORS" -t sentinel/vision/test-cyber/events -m "$(event test-cyber "$ID_BLOCK")" >/dev/null
mqtt_pub $CA -V mqttv5 -q 1 -u vision -P "$VISIONPW" -t sentinel/vision/test-cyber/events -m "$(event test-cyber "$ID_OK")" >/dev/null
sleep 3
check "Compte 'sensors' publiant un événement vision : non stocké" absent "$(stored "$ID_BLOCK")"
check "Témoin : compte 'vision' autorisé : stocké" present "$(stored "$ID_OK")"

echo; echo "3. API : authentification des producteurs"
check "POST sans jeton" 401 "$(http -X POST -H 'Content-Type: application/json' --data "$(telemetry "$RUN_ID-a" 20)" $API/api/telemetry)"
check "POST avec un faux jeton" 401 "$(http -X POST -H 'Authorization: Bearer faux' -H 'Content-Type: application/json' --data "$(telemetry "$RUN_ID-b" 20)" $API/api/telemetry)"
check "POST avec le jeton d'un autre rôle (vision -> mesures)" 401 "$(http -X POST -H "Authorization: Bearer $VISIONPW" -H 'Content-Type: application/json' --data "$(telemetry "$RUN_ID-c" 20)" $API/api/telemetry)"

echo; echo "4. API : validation des données"
AUTH=(-H "Authorization: Bearer $SENSORS" -H 'Content-Type: application/json')
check "JSON mal formé" 422 "$(http -X POST "${AUTH[@]}" --data '{invalide' $API/api/telemetry)"
check "Température hors limites (999 °C)" 422 "$(http -X POST "${AUTH[@]}" --data "$(telemetry "$RUN_ID-d" 999)" $API/api/telemetry)"
check "Champ inconnu injecté" 422 "$(http -X POST "${AUTH[@]}" --data '{"device_id":"test-cyber","message_id":"x","observed_at":"'$NOW'","simulated":true,"temperature_c":20,"admin":true}' $API/api/telemetry)"
check "Message trop gros (20 Ko)" 413 "$(head -c 20000 /dev/zero | tr '\0' 'a' | curl -s -o /dev/null -w '%{http_code}' -X POST "${AUTH[@]}" --data-binary @- $API/api/telemetry)"
FIRST=$(curl -s -X POST "${AUTH[@]}" --data "$(telemetry "$RUN_ID-dup" 21)" $API/api/telemetry)
SECOND=$(curl -s -X POST "${AUTH[@]}" --data "$(telemetry "$RUN_ID-dup" 21)" $API/api/telemetry)
echo "$SECOND" | grep -q '"inserted":false' && echo "$FIRST" | grep -q '"inserted":true' \
  && ok "Rejeu du même message : pas de doublon" || ko "Rejeu du même message : doublon ou erreur ($FIRST / $SECOND)"

echo; echo "5. Correctifs de l'étape 2"
check "Documentation /docs de l'API masquée" 404 "$(http $API/docs)"
check "Service vision : données non JPEG refusées" 415 "$(http -X POST -H 'Content-Type: text/plain' --data test $VISION/analyze)"

echo; echo "6. Grafana et base de données"
check "Grafana sans connexion" 401 "$(http $GRAFANA/api/search)"
if $DC exec -T -e PGPASSWORD="$GRAFANADB" postgres psql -h 127.0.0.1 -U grafana_reader -d sentinel -c \
   "INSERT INTO security_events(received_at,reason,transport) VALUES(0,'test','test')" >/dev/null 2>&1; then
  ko "Compte Grafana capable d'écrire en base"
else
  ok "Compte Grafana en lecture seule : écriture refusée"
fi

echo; echo "7. Exposition réseau"
for port in 5432 9090; do check "Port $port (interne) non publié sur la VM" ferme "$(port_open 127.0.0.1 $port)"; done
IP=$(hostname -I | awk '{print $1}')
for port in 3000 8080 8090 8883; do check "Port $port non joignable depuis le réseau ($IP)" ferme "$(port_open "$IP" $port)"; done

echo; echo "8. Limitation de débit (dernier test : bloque le compte 'sensors' en HTTP pendant 1 minute)"
LIMITED=0
for i in $(seq 1 125); do
  [ "$(http -X POST "${AUTH[@]}" --data "$(telemetry "$RUN_ID-rate" 22)" $API/api/telemetry)" = 429 ] && LIMITED=$((LIMITED+1))
done
[ "$LIMITED" -gt 0 ] && ok "Rafale de 125 requêtes : $LIMITED bloquées (429)" || ko "Rafale de 125 requêtes : aucune bloquée"

echo; echo "=== Résultat : $PASS OK, $FAIL échec(s) - détail enregistré dans $OUT ==="
echo "Les rejets apparaissent dans Grafana, panneau des événements de sécurité."
