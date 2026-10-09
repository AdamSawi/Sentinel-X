# Simulation

Remplace le matériel absent par des sources et actionneurs virtuels.

Proposition : Python + NumPy pour les mesures, Paho MQTT pour les échanges, scénarios JSON pour la chronologie.

Prévoir phases normales, dérives, pics isolés, pertes de messages et arrêts de device. Chaque exécution possède une graine, un identifiant et une vérité terrain réservée à l’évaluation. Employer un indice de gaz synthétique sans prétendre reproduire une calibration réelle de MQ-2.

Les commandes modifient les états virtuels LED/buzzer et produisent un accusé de réception. Les vidéos sont rejouées à cadence contrôlée et analysées par le backend. Documenter leur provenance et leurs droits ; ne pas versionner de gros fichiers ou de données sensibles.

Distinguer temps du scénario et temps réel de réception, notamment en lecture accélérée. Utiliser des identifiants de messages et d’exécutions pour relier les événements.

## Simulation thermique intégrée

Le service Docker reprend `server.py` et `index.html` du collègue. `integration.py` ajoute MQTTS et le réglage de la température sans modifier son modèle.

```sh
docker compose up --build -d --wait
```

Dans Grafana (http://localhost:3000), le panneau **SIMULATION** permet de déplacer le curseur de 0 à 100 °C. Relâcher le curseur applique la consigne. Le contrôle est aussi accessible sur http://localhost:8091/control et le dashboard original sur http://localhost:8091/dashboard/.

Une mesure est publiée chaque seconde : simulation → MQTTS → backend → PostgreSQL → Grafana (rafraîchissement toutes les cinq secondes). La consigne initiale est 25 °C et revient à cette valeur au redémarrage. Le panneau de dernière mesure affiche une absence de données après dix secondes sans réception.

La base SQLite et la prédiction du collègue restent dans le volume `simulation-data` ; les mesures Grafana sont conservées dans PostgreSQL.

Pour démontrer la chaîne : régler 25 °C, puis 50 °C, puis 80 °C, et vérifier la dernière valeur et la courbe dans Grafana. Le seuil thermique du modèle original est 70 °C.

## Circuit animé en direct

Le panneau Grafana intègre un schéma animé local : capteur de température, carte ESP8266 virtuelle, LED et alarme. Il s'agit d'une visualisation logicielle, pas d'un circuit Tinkercad/Wokwi ni d'une exécution de firmware Arduino.

Le flux `/live` transmet les mesures publiées et la prédiction réelle de `server.py` chaque seconde. La LED devient verte en situation normale, orange si le modèle prévoit une surchauffe, et rouge clignotante si la température mesurée dépasse 70 °C. Le bouton son active une alarme locale pendant une surchauffe actuelle ; le navigateur exige cette action pour autoriser le son. Sans données récentes ou connexion MQTT, le schéma passe en gris et l'alarme s'arrête.

Le curseur règle la consigne. L'affichage du capteur attend la prochaine mesure effectivement publiée via MQTTS, au lieu de simplement recopier le curseur. Les courbes Grafana restent alimentées par PostgreSQL.
