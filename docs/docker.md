# Grafana, Prometheus et intégration

## Lancer

Docker Desktop démarré ou Docker Engine avec Compose v2 :

```sh
docker compose up --build -d --remove-orphans --wait
docker compose ps
```

`--remove-orphans` retire l’ancien conteneur frontend s’il existe. Le code HTML/CSS/JavaScript maison est supprimé du dépôt ; son historique reste dans Git.

- **Grafana : http://localhost:3000**
- **Vision IA / caméra : http://localhost:8090**
- **API : http://localhost:8080**
- MQTT TLS : localhost:8883
- MQTT WebSocket TLS : port 9001 interne au réseau Docker

Le service vision YOLO/MediaPipe est lancé automatiquement. Dans Grafana, cliquer sur **ACTIVER LA CAMÉRA** puis autoriser la webcam. Le navigateur transmet les images au conteneur ; aucun notebook Jupyter n’est requis. Les simulateurs de capteurs restent des producteurs séparés.

## Accès Grafana

Utilisateur : **admin**. Le mot de passe est généré localement ; pour l’afficher dans votre terminal :

```sh
docker compose exec mqtt cat /run/sentinel/grafana-admin.password
```

Ne pas copier ce secret dans Git ou dans les logs du projet. Après connexion, ouvrir le dashboard **Sentinel-X · Centre de contrôle** dans le dossier Sentinel-X. Les sources et le dashboard sont provisionnés automatiquement ; aucune configuration manuelle de source n’est nécessaire.

La configuration du dashboard appartient à `infra/grafana/dashboards/sentinel.json`. Pour une modification durable, éditer ce fichier dans Git ; enregistrer depuis l’interface est désactivé pour ce dashboard provisionné.

## Deux sources, deux usages

| Source Grafana | Contenu | Chemin |
| --- | --- | --- |
| Prometheus | Disponibilité, débit d’ingestion, rejets, compteurs de détections et latence API | API /metrics → scrape toutes les 5 s → Prometheus → Grafana |
| PostgreSQL | Courbes, dates, zones, descriptions, confiance et événements de sécurité | Producteur → ingestion API/MQTT → PostgreSQL → Grafana en lecture seule |

Le scraping ne récupère pas les incidents un par un. Ceux-ci sont enregistrés dès leur réception. Les compteurs Prometheus démarrent à zéro avec le processus ; les rapports SQL restent persistants. Les taux calculés par Prometheus nécessitent plusieurs scrapes et sont des estimations sur leur fenêtre.

Les rapports suivent la période choisie dans Grafana et affichent au plus les 500 dernières lignes. Pour un export CSV, utiliser l’inspection des données du panneau ; ce n’est pas un export complet au-delà de cette limite. Les courbes utilisent l’heure de réception serveur. L’heure d’observation du producteur est conservée séparément.

Un heartbeat récent indique seulement que le composant publie encore, pas la qualité de son modèle. Sans heartbeat, on ne déduit pas son état de l’absence d’intrusions.

## Stockage et migration

PostgreSQL stocke `observations` et `security_events`. Le compte de l’API peut lire/insérer ; `grafana_reader` peut uniquement lire. PostgreSQL et Prometheus n’ont pas de port publié sur l’hôte.

Si l’ancien volume SQLite contient des observations, elles sont importées au démarrage de l’API. La clé kind/device/message_id évite les doublons. Le volume SQLite reste monté en lecture seule, n’est pas supprimé et n’est plus la base active. Les identifiants numériques internes peuvent changer lors de la migration.

Les volumes conservent PostgreSQL, Prometheus, Grafana, MQTT et les secrets. `docker compose down` les préserve. **Ne pas utiliser `down -v` pour un arrêt ordinaire.**

Les scripts PostgreSQL d’initialisation ne s’exécutent que sur un volume neuf. Ne pas changer simplement les mots de passe dans credentials pour des services déjà initialisés : leur rotation exige également une mise à jour dans PostgreSQL/Grafana.

## Identifiants des producteurs

Comptes MQTT : `sensors` pour les mesures, `vision` pour les événements, `backend` pour la lecture. Les mots de passe sensors/vision servent aussi de jetons Bearer pour leurs endpoints HTTP.

Créer un dossier local credentials, ignoré par Git, puis exporter seulement ce dont chaque collègue a besoin :

```sh
mkdir credentials
docker compose cp mqtt:/run/sentinel/server.crt credentials/server.crt
docker compose cp mqtt:/run/sentinel/sensors.password credentials/sensors.password
docker compose cp mqtt:/run/sentinel/vision.password credentials/vision.password
```

Ne pas partager les mots de passe PostgreSQL, Grafana, backend ou la clé privée MQTT. Le certificat autosigné est valable un an pour localhost, 127.0.0.1 et mqtt. Les clients doivent lui faire confiance explicitement ; ne pas désactiver TLS. Une extension Tinkercad peut utiliser WSS, mais son raccordement reste à tester par l’équipe.

## Mesures

Topic MQTT : `sentinel/sensors/<device_id>/telemetry`, QoS 1, sans retain.
Alternative : `POST http://localhost:8080/api/telemetry` avec `Authorization: Bearer <mot de passe sensors>`.

```json
{
  "device_id": "capteurs-01",
  "message_id": "mesure-unique-0001",
  "observed_at": "2026-10-06T12:00:00Z",
  "simulated": true,
  "temperature_c": 24.5,
  "humidity_pct": 48.0,
  "gas_index": 32.0,
  "presence": false
}
```

Température obligatoire ; humidité, indice gaz et présence facultatifs. Le gaz est un indice déclaré, pas une concentration calibrée. Le device doit correspondre au topic. Utiliser un nouvel identifiant par observation (UUID conseillé) ; un renvoi du même identifiant n’ajoute pas de doublon.

## Intrusions et anomalies

Topic MQTT : `sentinel/vision/<device_id>/events`, compte vision.
Alternative : `POST http://localhost:8080/api/events` avec `Authorization: Bearer <mot de passe vision>`.

```json
{
  "device_id": "vision-01",
  "message_id": "evenement-unique-0001",
  "observed_at": "2026-10-06T12:00:00Z",
  "simulated": true,
  "event_type": "intrusion",
  "zone": "zone-interdite",
  "confidence": 0.92,
  "description": "Personne détectée dans la zone"
}
```

Types acceptés : `intrusion`, `anomaly`, `presence`, `heartbeat`. Même contrat pour une anomalie calculée par le collègue : changer event_type, source, zone et description. Le nom historique du compte/topic vision est conservé pour compatibilité.

Confiance facultative entre 0 et 1 ; ne pas y placer un score d’anomalie non normalisé. Envoyer un heartbeat toutes les 5 secondes pour la fraîcheur du composant. Les vidéos rejouées et capteurs simulés utilisent simulated=true. L’API ajoute received_at (secondes Unix) et conserve observed_at avec fuseau.

Les POST utilisent Content-Type: application/json. Le service vision intégré produit automatiquement ce format ; le contrat reste disponible pour les autres modèles de l’équipe.

## Sécurité et limites

- MQTT est chiffré et authentifié ; les ACL distinguent capteurs et événements, pas chaque device.
- Rejets d’authentification HTTP, de validation et d’ingestion enregistrés sans message brut ni jeton. Les rejets propres au broker ne sont pas encore centralisés ; ils restent dans ses logs.
- 16 Kio maximum par message ; 120 messages/minute par flux MQTT et 120 requêtes/minute par rôle HTTP authentifié.
- Ports limités à 127.0.0.1. Grafana exige une connexion. L’API HTTP locale n’authentifie pas ses routes de lecture ; PostgreSQL/Prometheus communiquent en clair sur le réseau Docker interne.
- Un accès depuis les PC des collègues demande une configuration réseau et HTTPS adaptée. Ne pas remplacer les adresses d’écoute à l’aveugle.
- Pas de supervision CPU/RAM de l’hôte, d’IDS, de commandes d’actionneurs ou de règles d’alerte Grafana préconfigurées. Les tableaux présentent les résultats reçus.
- Prometheus conserve 15 jours ; pas de purge automatique PostgreSQL à ce stade.

## Vérifications

```sh
docker compose exec backend python smoke.py
docker compose exec backend python monitoring_check.py
docker compose logs --tail=50 backend vision mqtt postgres prometheus grafana
docker compose down
```

Le smoke test envoie des fixtures explicitement simulées et vérifie les permissions, rejets, doublons et métriques. Le second contrôle vérifie le scrape, les sources Grafana, les requêtes des panneaux et les droits SQL en lecture seule. La santé du service vision est contrôlée par Compose ; son endpoint `/analyze` peut être testé avec une image JPEG.

Ports configurables dans un `.env` local : `API_PORT` (8080), `GRAFANA_PORT` (3000), `MQTT_PORT` (8883), `VISION_PORT` (8090).
