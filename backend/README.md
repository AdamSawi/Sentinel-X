# Backend

Regroupe l’ingestion, l’API et le stockage. Les simulateurs et les modèles restent développés par les collègues ; ce service reçoit leurs mesures et résultats.

Implémentation : Python, FastAPI, Paho MQTT et SQLite.

- Valider les mesures MQTT et conserver les horodatages.
- Recevoir les événements d’analyse sans exécuter de modèle.
- Stocker mesures, événements, incidents et commandes.
- Exposer les données au frontend ; les commandes restent à intégrer ultérieurement.
- Fournir les heures de réception et les contrôles de santé ; compter les rejets depuis le démarrage.
- Retourner les historiques récents en JSON. Acquittement et exports dédiés restent à développer.

Les modèles ne reçoivent pas les étiquettes de scénario. SQLite reste interne au backend et persiste via un volume ; documenter les migrations et les limites de concurrence si l’architecture évolue.

L’API de réception est implémentée dans `app.py` : validation, persistance SQLite, abonnement MQTT TLS et routes de lecture pour le monitoring. Elle ne contient aucun modèle d’analyse ou de détection.

Lancement et formats attendus : [guide Docker](../docs/docker.md). Vérification de l’intégration : `docker compose exec backend python smoke.py` (fixtures de test explicitement marquées simulées).
