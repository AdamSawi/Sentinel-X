# API et stockage

FastAPI reçoit les mesures des capteurs et les résultats des composants des collègues par MQTT TLS ou HTTP. Aucun simulateur ni algorithme de détection n’est implémenté ici.

- Validation et déduplication des observations.
- Stockage dans PostgreSQL, avec heures d’observation et de réception.
- Routes de lecture et endpoints d’ingestion authentifiés.
- Exposition Prometheus sur `/metrics` : disponibilité MQTT/base, volumes acceptés, types d’événements, rejets et latence HTTP.
- Historique des rejets API/ingestion dans `security_events`, sans secrets ni contenu brut des messages.
- Migration idempotente de l’ancienne base SQLite si elle existe dans le volume conservé en lecture seule.

Les contrats existants restent compatibles. Le type d’événement `anomaly` est maintenant accepté en complément de `intrusion`, `presence` et `heartbeat` : le producteur calcule le résultat, l’API l’enregistre.

Voir le [guide Docker](../docs/docker.md). Tests : `docker compose exec backend python smoke.py`, puis `docker compose exec backend python monitoring_check.py`.
