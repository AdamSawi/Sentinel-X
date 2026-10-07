# Rapport cybersécurité — Sentinel-X / The Watcher

> Workshop national EPSI BAC+4 — Mission Sentinel-X — Octobre 2026
> Partie cybersécurité — rédigé par Nico

## 1. Contexte et périmètre

The Watcher est un prototype entièrement logiciel : capteurs simulés, analyse vidéo par webcam, stockage et supervision dans un dashboard Grafana. L'ensemble tourne dans Docker Compose sur une seule machine (le PC d'un apprenant, ici une VM Ubuntu).

**Périmètre évalué :** les 6 services du fichier `compose.yaml` (Mosquitto, API backend, PostgreSQL, Prometheus, Grafana, service vision) dans leur configuration de démonstration locale.

**Hors périmètre :** le matériel du sujet original (ESP8266, boîtier), non réalisé ; un déploiement exposé sur un réseau ou sur Internet.

Tous les tests ont été réalisés **uniquement sur notre propre environnement local**.

## 2. Architecture et surface d'attaque

| Service | Rôle | Exposition |
| --- | --- | --- |
| Mosquitto | Réception des mesures et événements (MQTT) | `127.0.0.1:8883`, TLS obligatoire |
| API backend | Validation, stockage, métriques | `127.0.0.1:8080` |
| Service vision | Analyse YOLO / MediaPipe des images webcam | `127.0.0.1:8090` |
| Grafana | Dashboard de supervision | `127.0.0.1:3000`, connexion obligatoire |
| PostgreSQL | Base de données | Réseau Docker interne uniquement |
| Prometheus | Collecte des métriques | Réseau Docker interne uniquement |

Points d'entrée possibles pour un attaquant : les 4 ports publiés, les messages envoyés par les producteurs (capteurs, vision), le navigateur de l'utilisateur (pages web malveillantes) et le dépôt Git (fuite de secrets).

## 3. Analyse de risques

Échelle : probabilité et impact de 1 (faible) à 3 (élevé). Le niveau correspond au risque **avant** mesures.

| # | Scénario de menace | Actif visé | Prob. | Impact | Niveau | Mesures |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | Interception ou falsification des mesures en transit | Intégrité des données capteurs | 2 | 3 | Élevé | MQTT en TLS, aucun port en clair |
| R2 | Envoi de fausses mesures ou de fausses intrusions | Fiabilité des alertes | 3 | 3 | Élevé | Authentification MQTT et API, ACL par rôle |
| R3 | Message piégé (format invalide, valeurs aberrantes, taille) | Disponibilité, base de données | 3 | 2 | Élevé | Validation stricte, limite de 16 Kio, rejet tracé |
| R4 | Inondation de messages (déni de service) | Disponibilité | 2 | 2 | Moyen | Limitation à 120 messages/min par flux |
| R5 | Accès au dashboard ou modification des données | Confidentialité, intégrité | 2 | 3 | Élevé | Connexion Grafana obligatoire, compte SQL en lecture seule |
| R6 | Accès direct à la base ou aux métriques | Confidentialité | 2 | 3 | Élevé | PostgreSQL et Prometheus non publiés |
| R7 | Fuite de mots de passe ou de clés via Git | Tous les secrets | 2 | 3 | Élevé | Secrets générés au démarrage, `.gitignore` |
| R8 | Reconnaissance de l'API (liste des routes) | Facilite les autres attaques | 3 | 1 | Moyen | Documentation `/docs` désactivée (correctif) |
| R9 | Page web malveillante créant de fausses détections vision | Fiabilité des alertes | 2 | 2 | Moyen | Seules les images JPEG sont acceptées (correctif) |
| R10 | Accès aux services depuis le réseau local | Tous les services | 2 | 3 | Élevé | Ports liés à `127.0.0.1` uniquement |
| R11 | Collecte d'images de personnes (visages) | Vie privée (RGPD) | 2 | 2 | Moyen | Images analysées en mémoire, non stockées ; seuls des compteurs sont enregistrés |

## 4. Mesures de sécurité en place

| Mesure | Où dans le dépôt |
| --- | --- |
| MQTT chiffré en TLS (version 1.2 imposée), connexion anonyme interdite | `infra/mosquitto.conf` |
| Un compte par rôle (backend, capteurs, vision) avec droits limités (ACL) | `infra/acl` |
| Mots de passe aléatoires générés au premier démarrage, jamais dans Git | `infra/start.sh` |
| Jetons d'accès pour l'API, comparés en temps constant | `backend/app.py`, fonction `authorized` |
| Validation stricte des messages (types, bornes, champs inconnus refusés) | `backend/app.py`, classes `Telemetry` et `Intrusion` |
| Taille maximale de 16 Kio par message, 120 messages/min par flux | `backend/app.py`, `infra/mosquitto.conf` |
| Chaque rejet est enregistré (sans le message brut ni le jeton) et visible dans Grafana | Table `security_events` |
| Compte PostgreSQL de l'application sans droit de modifier le schéma, compte Grafana en lecture seule | `infra/postgres/init.sh` |
| Ports publiés uniquement sur `127.0.0.1` ; base et Prometheus internes | `compose.yaml` |
| Conteneurs sans élévation de privilèges, API et vision en système de fichiers en lecture seule, utilisateurs non root | `compose.yaml`, Dockerfiles |
| Grafana : inscription et accès anonyme désactivés | `compose.yaml` |

## 5. Correctifs apportés

| Problème identifié | Correctif | Preuve |
| --- | --- | --- |
| Rien n'empêchait de commiter une clé privée | Ajout de `*.key` et `*.pem` au `.gitignore` | `git diff` |
| La page `/docs` de l'API listait toutes les routes (HTTP 200) | Documentation automatique désactivée dans `backend/app.py` | HTTP 404 |
| Le service vision acceptait n'importe quelles données. Une page web malveillante pouvait lui envoyer des requêtes sans déclencher de contrôle du navigateur et créer de fausses détections | Seul `Content-Type: image/jpeg` est accepté dans `modeles-ia/service.py` | HTTP 415 |

## 6. Tests de sécurité

Les tests sont automatisés dans `cybersecurite/tests-cyber.sh` et rejouables à tout moment. Résultat du 07/10/2026 : **25 tests réussis sur 25**. Détail complet : `cybersecurite/resultats-tests-20261007-1511.txt`.

| Catégorie | Attaques testées | Résultat |
| --- | --- | --- |
| MQTT | Connexion anonyme, mauvais mot de passe, connexion sans TLS, port en clair 1883 | 4/4 bloquées |
| Droits MQTT | Le compte capteurs se fait passer pour la caméra (avec un témoin autorisé) | Bloqué, témoin accepté |
| Authentification API | Sans jeton, faux jeton, jeton d'un autre rôle | 3/3 refusées (401) |
| Données piégées | JSON cassé, 999 °C, champ inconnu, 20 Ko, rejeu du même message | 5/5 refusées ou dédoublonnées |
| Correctifs | `/docs`, données non JPEG vers la vision | 404 et 415 |
| Grafana et base | Accès sans connexion, écriture avec le compte en lecture seule | 2/2 refusés |
| Exposition réseau | Ports internes, accès aux 4 ports depuis l'IP réseau de la VM | 6/6 fermés |
| Inondation | Rafale de 125 requêtes | Requêtes au-delà de la limite bloquées (429) |

## 7. Risques résiduels et recommandations pour la production

Ces points sont **acceptés pour une démonstration locale**, mais devraient être traités avant tout déploiement réel.

| Risque résiduel | Recommandation |
| --- | --- |
| Certificat MQTT autosigné généré automatiquement | Utiliser notre CA interne (`cybersecurite/`) pour signer les certificats, distribuer `ca.crt` aux clients |
| API, Grafana et vision en HTTP (sans chiffrement) | HTTPS via un reverse proxy (Nginx, Traefik) avec certificats de la CA |
| Échanges internes PostgreSQL / Prometheus en clair | TLS sur PostgreSQL ; acceptable tant que le réseau Docker reste isolé |
| Routes de lecture de l'API et `/metrics` sans authentification | Ajouter un jeton ou les réserver au réseau interne |
| ACL par rôle et non par capteur : un capteur peut publier au nom d'un autre | Un compte et un certificat client par appareil (mTLS) |
| Service vision sans authentification ni limite de débit | Jeton d'accès et limitation de débit |
| Échecs d'authentification non limités (inondation de la table des rejets) | Limiter aussi les tentatives échouées |
| HTML non filtré dans Grafana (nécessaire pour la caméra) | Aucun compte éditeur ; en production, intégrer la caméra autrement |
| Rejets du broker MQTT non centralisés dans Grafana | Collecter les logs Mosquitto (Loki ou équivalent) |
| Pas de détection d'intrusion ni d'alertes automatiques | Règles d'alerte Grafana, IDS réseau (Suricata) |
| Pas de rotation des secrets ni de sauvegarde | Procédure de rotation, sauvegardes chiffrées de PostgreSQL |
| Capabilities Linux par défaut dans les conteneurs | `cap_drop: [ALL]` service par service, images épinglées par empreinte |

## 8. Conclusion

Le prototype applique les principes de défense en profondeur adaptés à son contexte : chiffrement et authentification des échanges, moindre privilège, validation des entrées, traçabilité des rejets et exposition minimale. Trois faiblesses ont été corrigées pendant le workshop et 25 tests automatisés prouvent que les contrôles fonctionnent réellement.

Les limites restantes sont identifiées et assumées pour une démonstration locale. Elles constituent la feuille de route sécurité d'un éventuel passage en production.
