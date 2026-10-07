# Vision IA conteneurisée

Le dossier conserve sans modification les notebooks fournis par le collègue :

- `facialRecognition.ipynb` : détection de visages MediaPipe ;
- `facialRecognition_yolo.ipynb` : détection de personnes YOLO et analyse faciale.

La démonstration intégrée n’exécute pas Jupyter. Le service Docker `vision` reprend la même approche avec YOLO11n et MediaPipe dans un processus adapté au déploiement.

## Fonctionnement

Docker Desktop sous Windows ne transmet pas directement la webcam aux conteneurs Linux. La page caméra ouverte dans Grafana utilise donc l’API navigateur `getUserMedia` :

```text
Webcam Windows → navigateur → service vision Docker
                ← image annotée ← YOLO + MediaPipe
                                      ↓
                               API Sentinel-X
                                      ↓
                            PostgreSQL / Prometheus
```

Seules des images temporaires sont traitées en mémoire. Elles ne sont ni stockées en base ni écrites sur disque. L’API reçoit uniquement les métadonnées de détection.

## Lancement

Depuis la racine du dépôt :

```sh
docker compose up --build -d --remove-orphans --wait
```

Ouvrir ensuite `http://localhost:3000/d/sentinel-overview`, puis cliquer sur **ACTIVER LA CAMÉRA** dans le panneau vidéo et autoriser la webcam. Le premier build est plus long, car il installe les bibliothèques CPU et télécharge les deux modèles dans l’image Docker.

Le service vision est également consultable directement sur `http://localhost:8090`. Cet accès permet de tester séparément la permission caméra si le navigateur la bloque dans l’iframe Grafana.

## Contrat produit

Chaque présence détectée génère au maximum un événement par seconde avec : nombre de personnes, nombre de visages, confiance YOLO et temps de traitement. Le backend valide et stocke ces métadonnées, puis alimente les vues PostgreSQL et les métriques Prometheus du dashboard.

Le service utilise le CPU par défaut pour rester compatible avec Docker Desktop sans configuration CUDA. Les réglages sont volontairement limités à 640×360 côté navigateur et `imgsz=640` côté YOLO afin de préserver la stabilité de la démonstration.

## Variante NVIDIA

Le lancement standard reste en CPU. Sur un poste Windows avec une carte NVIDIA, les pilotes compatibles WSL2 et l’accès GPU activé dans Docker Desktop, lancer :

```sh
docker compose -f compose.yaml -f compose.gpu.yaml up --build -d --remove-orphans --wait
```

Cette surcharge remplace uniquement l’image du service `vision` par une image PyTorch CUDA et sélectionne le GPU `0`. Grafana, l’API et les autres services restent identiques.
