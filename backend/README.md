# Backend

Regroupe l’ingestion, l’API, les modèles IA, les alertes et le stockage, auparavant séparés dans `api`, `modeles-ia` et `database`.

Proposition : Python, FastAPI et SQLite. Organiser le code par responsabilité au fil de l’implémentation.

- Valider les mesures MQTT et conserver les horodatages.
- Analyser réellement les fenêtres temporelles et les images des vidéos rejouées.
- Stocker mesures, événements, incidents et commandes.
- Exposer les données au frontend et autoriser les commandes avec retour d’état.
- Détecter les sources périmées, journaliser les rejets et distinguer acquittement et résolution.
- Fournir exports CSV/JSON et mesures de performance.

Les modèles ne reçoivent pas les étiquettes de scénario. SQLite reste interne au backend et persiste via un volume ; documenter les migrations et les limites de concurrence si l’architecture évolue.

Aucun backend exécutable n’est encore présent. Ajouter configuration, contrats d’interface et commandes avec le code.
