# API et ingestion

Ce dossier accueille le backend et la réception des données issues du broker MQTT.

- Valider les messages et conserver leurs heures de mesure et de réception.
- Stocker les mesures et fournir les données nécessaires aux modèles IA.
- Exposer les mesures, résultats IA, incidents et états des services au frontend.
- Gérer les alertes, leur acquittement et les commandes authentifiées vers l’ESP8266.
- Appliquer les droits, limites de débit et traces d’audit.

Le framework reste à choisir. Documenter les endpoints, formats d’échange et commandes de lancement lors de leur implémentation.
