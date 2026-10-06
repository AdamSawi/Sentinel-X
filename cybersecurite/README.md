# Cybersécurité

Ce dossier accueille les travaux de cybersécurité de l’équipe Sentinel-X :

- Analyse des risques et périmètre des tests autorisés.
- Vérification du chiffrement, de l’authentification et des droits d’accès.
- Audit des configurations réseau, Docker et des services.
- Tests de validation des messages et de résistance aux abus.
- Rapport de pentest, preuves, corrections et résultats de vérification.

Les configurations de déploiement restent dans `infra/` et les contrôles applicatifs dans `backend/`. Documenter ici les constats et les recommandations associés.

Ne pas versionner de secrets, clés privées ou captures contenant des identifiants. Réaliser les tests uniquement sur le périmètre autorisé du projet.
