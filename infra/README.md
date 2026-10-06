# Infrastructure et monitoring

Cinq services dans `compose.yaml` :

- Mosquitto : MQTT TLS, WebSocket TLS, authentification et ACL.
- PostgreSQL : observations et historique des rejets ; aucun port publié sur l’hôte.
- Backend : ingestion et exposition de métriques, sans modèle ni simulateur.
- Prometheus : scrape de `backend:8000/metrics` toutes les 5 secondes, rétention 15 jours.
- Grafana : interface unique, sources et dashboard provisionnés depuis `infra/grafana/`.

Les mots de passe et le certificat local sont générés au premier démarrage et conservés dans le volume credentials. Le compte PostgreSQL de Grafana possède seulement SELECT. L’application utilise un compte distinct sans droit de modifier le schéma. Les ports publiés sont limités à localhost.

Grafana : http://localhost:3000. API : http://localhost:8080. Pour les identifiants et les contrats : [guide Docker](../docs/docker.md).

Le réseau Docker interne PostgreSQL/Prometheus utilise des communications non chiffrées. MQTT est chiffré. L’API HTTP reste locale ; ne pas présenter cette base comme un déploiement entièrement durci ou exposable à Internet.
