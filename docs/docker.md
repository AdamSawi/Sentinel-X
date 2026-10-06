# Lancement et connexion des composants

## Démarrer

Installer Docker Engine avec Compose v2 ou Docker Desktop démarré. Depuis la racine :

```sh
docker compose up --build -d
docker compose ps
```

Ouvrir **http://localhost:8080**. Le premier build télécharge les images et dépendances. Le broker génère automatiquement des mots de passe aléatoires et un certificat local ; les prochains démarrages les réutilisent.

Le dashboard démarre sans données. Les simulateurs et la détection sont développés par les collègues ; cette stack reçoit leurs résultats sans les remplacer. Aucun générateur ni modèle de détection n’est ajouté.

## Services

| Service | Accès | Fonction |
| --- | --- | --- |
| front | http://localhost:8080 | Interface et proxy de l’API |
| backend | backend:8000, interne Docker | FastAPI, ingestion et SQLite |
| mqtt | localhost:8883 | MQTT avec TLS, identifiants et ACL |
| mqtt | wss://localhost:9001 | MQTT sur WebSocket TLS, pour une passerelle navigateur |

SQLite, certificats, mots de passe et persistance MQTT utilisent des volumes Docker. `docker compose down` conserve ces volumes. **Ne pas ajouter `-v` pour un arrêt ordinaire : cela effacerait données et identifiants.**

Les ports sont liés à 127.0.0.1 : cette base est destinée à une démonstration sur un PC. HTTP sert localement le dashboard et l’API. Avant un accès depuis un autre PC, prévoir HTTPS, authentification de lecture, règles réseau, certificat correspondant au nom du serveur et mise à jour des publications de ports. Ne pas simplement exposer les ports à tous les réseaux.

## Identifiants des producteurs

Trois comptes MQTT sont créés : `sensors` publie les mesures ; `vision` publie les événements ; `backend` lit les deux flux. Les identifiants des producteurs servent également de jetons Bearer sur leur endpoint HTTP respectif.

Créer localement un dossier `credentials` (ignoré par Git), puis exporter uniquement les fichiers nécessaires :

```sh
mkdir credentials
docker compose cp mqtt:/run/sentinel/server.crt credentials/server.crt
docker compose cp mqtt:/run/sentinel/sensors.password credentials/sensors.password
docker compose cp mqtt:/run/sentinel/vision.password credentials/vision.password
```

Le collègue capteurs utilise `sensors.password` ; le collègue intrusion utilise `vision.password`. Ne pas partager la clé privée serveur ni le compte backend. Ne pas copier les secrets dans le code ou Git.

Le certificat autosigné, valide un an, contient localhost, 127.0.0.1 et mqtt. Les clients Python le chargent comme certificat de confiance. Les navigateurs nécessitent de lui faire confiance explicitement pour WSS ; la passerelle Tinkercad doit être testée dans le navigateur cible. Ne pas désactiver la vérification TLS. L’extension Tinkercad n’est ni installée ni intégrée par ce dépôt.

## Contrat capteurs

Publier du JSON UTF-8, QoS 1, sans retain, sur :

```text
sentinel/sensors/<device_id>/telemetry
```

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

`temperature_c` est obligatoire ; humidité, indice gaz et présence sont facultatifs. L’indice gaz n’est pas une concentration calibrée. `device_id` doit correspondre au topic. Une nouvelle mesure reçoit un nouvel identifiant ; renvoyer le même identifiant est idempotent. Les producteurs doivent conserver des identifiants uniques après redémarrage (UUID conseillé).

Alternative HTTP : `POST http://localhost:8080/api/telemetry` avec `Authorization: Bearer <contenu sensors.password>` et `Content-Type: application/json`.

## Contrat intrusion

Publier sur `sentinel/vision/<device_id>/events` avec le compte `vision`, ou envoyer ce même JSON par `POST /api/events` avec le jeton vision :

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

`event_type` accepte `intrusion`, `presence` et `heartbeat`. Émettre un heartbeat toutes les 5 secondes pour indiquer que le composant tourne ; sans heartbeat, sa santé est inconnue. `confidence` est facultative et comprise entre 0 et 1. Les sources vidéo rejouées utilisent `simulated: true`.

Le modèle reste dans le composant du collègue. Cette API reçoit ses résultats ; elle ne détecte aucune intrusion elle-même. Aucun flux vidéo n’est encore transporté. L’ingestion ajoute `received_at` (secondes Unix) et conserve `observed_at` avec fuseau horaire.

## Surveillance et limites

- Le dashboard interroge l’API toutes les 2 secondes ; il montre les 200 dernières mesures et les 100 derniers événements reçus.
- Les sources sont marquées périmées après 15 secondes. Un historique conservé n’est pas un signe de connexion active.
- Healthchecks Docker : MQTT authentifié, API et stockage accessibles, frontend relié au backend.
- MQTT tente de se reconnecter automatiquement après interruption du broker.
- Les messages sont limités à 16 Kio et validés. L’ingestion accepte au maximum 120 messages/minute par flux MQTT et 120 requêtes/minute par rôle HTTP authentifié. Réduire la cadence ou adapter explicitement ces limites si plusieurs devices sont ajoutés.
- Le compteur de rejets API/ingestion est réinitialisé au redémarrage. Il n’inclut pas tous les refus du broker ; consulter ses logs pour les connexions MQTT refusées.
- Les ACL séparent les rôles capteurs/vision, pas chaque device. La lecture du monitoring local n’est pas authentifiée. Cette base ne remplace pas le durcissement et le pentest du projet.
- Pas encore de modèle IA embarqué, d’actionneurs, de rétention automatique des observations ou de supervision CPU/RAM. Le dashboard affiche les données reçues, sans score de risque inventé.

## Vérifier et dépanner

```sh
docker compose exec backend python smoke.py
docker compose logs --tail=50 mqtt backend front
docker compose restart backend
docker compose down
```

Le smoke test passe par le proxy du frontend, publie une mesure en MQTT TLS, crée un événement via l’API, vérifie les refus de rôle/format et l’idempotence. Ses observations `smoke-*` restent dans l’historique avec le marqueur simulé.

Les ports peuvent être changés via `WEB_PORT`, `MQTT_PORT`, `MQTT_WS_PORT` dans un `.env` local. Les modèles des collègues pourront ensuite être ajoutés comme services Compose, en utilisant `mqtt:8883` ou `backend:8000` sur le réseau Docker.
