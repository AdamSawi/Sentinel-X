# Infrastructure et cybersécurité

Regroupe déploiement et responsabilités de l’ancien dossier `cyber`.

Préparer Docker Compose, Mosquitto avec TLS et authentification, volumes persistants, contrôles de santé et gestion des logs. Exposer seulement les ports nécessaires ; SQLite reste interne au backend.

Documenter certificats, droits MQTT, secrets fournis à l’exécution, isolation, firewall et SSH si utilisés. Les contrôles applicatifs de validation et d’autorisation sont dans le backend.

Démontrer de vrais refus de connexion, rejets de messages et pertes/reprises de services locaux. Collecter les événements constatés plutôt que des logs prédéfinis présentés comme des preuves.

Conserver le périmètre autorisé du pentest, les observations, corrections et vérifications sans secrets.

Le déploiement est disponible via `compose.yaml` à la racine. Le broker utilise TLS, trois comptes à droits distincts et des secrets générés au premier lancement. Les ports sont limités à localhost. Le backend et le frontend ont des healthchecks ; données et identifiants persistent dans des volumes.

Le [guide Docker](../docs/docker.md) décrit le lancement, les contrats et les limites de sécurité restant à traiter.
