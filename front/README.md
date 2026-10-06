# Frontend

Dashboard unique : mesures simulées, historiques, vidéo rejouée, résultats IA, incidents, santé des services et événements cyber.

Version initiale : HTML/CSS/JavaScript avec graphique Canvas, sans bibliothèque externe.

Afficher le mode simulation/rejeu. Une représentation 2D suffit pour montrer la zone, les présences et les états virtuels LED/buzzer. Les résultats et confirmations de commande viennent du backend.

Toutes les commandes passent par l’API authentifiée. Distinguer demandé et confirmé, acquitté et résolu, normal et indisponible. Prévoir des graphiques exportables pour le dossier.

L’interface est disponible sur http://localhost:8080 après `docker compose up --build -d`. Elle affiche les mesures, une courbe Canvas, les événements reçus et la santé API/SQLite/MQTT, avec actualisation toutes les deux secondes. Les états périmés sont signalés. Aucun modèle n’est exécuté dans le navigateur.

Les commandes d’actionneurs, la vidéo et les exports évoqués ci-dessus restent des objectifs futurs. Voir le [guide Docker](../docs/docker.md).
