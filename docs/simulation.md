# Simulation et démonstration

## Choix des outils

Simuler les sources physiques et faire fonctionner la chaîne logicielle : transport sécurisé, validation, stockage, analyse, affichage et commandes.

| Option | Utilité | Priorité |
| --- | --- | --- |
| Python + NumPy | Mesures bruitées, dérives et corrélations avec paramètres reproductibles | Premier choix |
| Paho MQTT + Mosquitto | Publier comme un device, recevoir des commandes et tester le transport réel | MVP |
| SimPy | Événements discrets, files, pannes et ressources partagées | Seulement si ces interactions sont nécessaires |
| Wokwi | Schéma interactif avec capteurs, OLED et actionneurs virtuels | Option après intégration |

Wokwi référence ESP32, DHT22, MQ-2, PIR, OLED et buzzer. L’ESP8266 n’apparaît pas dans sa liste actuelle : une démonstration ESP32 serait une adaptation. Vérifier séparément les conditions et moyens de connexion au broker local avant d’en dépendre.

Le générateur doit produire des variations temporelles cohérentes. Exemple : phase normale, montée lente du gaz, hausse de température puis récupération. Ces paramètres sont pédagogiques et ne constituent pas un modèle physique calibré.

## Vidéo et analyse

OpenCV lit les images d’un fichier vidéo ; un modèle de personnes traite ces images et détermine les entrées dans une zone. La source est rejouée, l’inférence est exécutée pendant la démonstration.

Prévoir des clips positifs et négatifs annotés, avec droits vérifiés. Respecter leur cadence ou annoncer l’accélération. Utiliser indice d’image et temps du scénario pour synchroniser vidéo et capteurs.

Pour les séries, comparer une référence temporelle simple (moyenne mobile, pente, écart à une référence normale) avec un modèle sur fenêtres multivariées, par exemple covariance robuste ou Isolation Forest. Le choix reste ouvert. Les étiquettes attendues ne sont pas des entrées du modèle.

Séparer réglage et évaluation par exécutions complètes, avec graines, amplitudes, bruit et durées différents. Éviter de répartir des fenêtres temporelles qui se chevauchent entre apprentissage et test.

## Résultats à présenter

| Figure ou preuve | Mesure |
| --- | --- |
| Courbes température/gaz avec zones d’incident et détection | Délai de détection et réaction aux dérives |
| Vidéo annotée et chronologie des présences | Présences détectées, manquées et fausses alertes |
| Tableau comparatif des approches | Détections et erreurs sur les mêmes scénarios réservés à l’évaluation |
| Distribution de latence | Médiane et percentile 95 du temps réel de traitement |
| Chronologie interruption/reprise | Détection de perte de source et récupération |
| Trace de message invalide et rejet associé | Contrôle de sécurité réellement appliqué |
| Commande et accusé de réception | Aller-retour complet vers l’actionneur virtuel |

Conserver les mesures en CSV/JSON. Plotly permet des graphiques interactifs et, via Kaleido et ses dépendances, des exports statiques. Mermaid sert aux schémas d’architecture. Joindre identifiant d’exécution, graine, paramètres, versions et caractéristiques du PC.

Mesurer les latences avec des horloges comparables et séparer temps réel et temps accéléré du scénario. Définir une fenêtre pour associer détections et incidents attendus ; regrouper les alertes répétées d’un même incident.

Les performances synthétiques ne prouvent pas une fiabilité sur un site industriel.

## Démo proposée en trois minutes

1. Montrer l’état normal et le trajet des mesures simulées.
2. Lancer une dérive reproductible ; afficher les courbes et l’alerte calculée.
3. Rejouer une entrée dans la zone ; afficher l’inférence vidéo.
4. Commander le buzzer virtuel et montrer le retour d’état.
5. Interrompre un device ou envoyer un message invalide ; montrer l’état dégradé ou le rejet.

Précharger vidéos et poids des modèles pour une démonstration sans téléchargement.

## Sources officielles

- [NumPy](https://numpy.org/doc/stable/reference/random/generator.html)
- [Paho MQTT Python](https://eclipse.dev/paho/clients/python/docs/)
- [SimPy](https://simpy.readthedocs.io/en/latest/index.html)
- [Wokwi : matériel pris en charge](https://docs.wokwi.com/getting-started/supported-hardware)
- [OpenCV : vidéos](https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html)
- [FastAPI](https://fastapi.tiangolo.com/)
- [scikit-learn : anomalies](https://scikit-learn.org/stable/modules/outlier_detection.html)
- [Plotly : exports](https://plotly.com/python/static-image-export/)
