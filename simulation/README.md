# Simulation

Remplace le matériel absent par des sources et actionneurs virtuels.

Proposition : Python + NumPy pour les mesures, Paho MQTT pour les échanges, scénarios JSON pour la chronologie.

Prévoir phases normales, dérives, pics isolés, pertes de messages et arrêts de device. Chaque exécution possède une graine, un identifiant et une vérité terrain réservée à l’évaluation. Employer un indice de gaz synthétique sans prétendre reproduire une calibration réelle de MQ-2.

Les commandes modifient les états virtuels LED/buzzer et produisent un accusé de réception. Les vidéos sont rejouées à cadence contrôlée et analysées par le backend. Documenter leur provenance et leurs droits ; ne pas versionner de gros fichiers ou de données sensibles.

Distinguer temps du scénario et temps réel de réception, notamment en lecture accélérée. Utiliser des identifiants de messages et d’exécutions pour relier les événements.

Aucun simulateur n’est encore implémenté. Voir le [guide](../docs/simulation.md).
