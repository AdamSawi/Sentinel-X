# 🔐 Sentinel-X — Mise en place de la PKI

> **Partie Cybersécurité** · Workshop national EPSI — Octobre 2026

## 🎯 Objectif

Mise en place d'une **autorité de certification (CA) interne**, utilisée pour signer un certificat serveur destiné au **chiffrement TLS** des échanges du projet (ESP8266 ↔ serveur, et/ou API).

## ✅ Résultat

La CA et le certificat serveur ont été générés et vérifiés avec succès :

```console
$ openssl verify -CAfile ca.crt server.crt
server.crt: OK
```

La chaîne de confiance est opérationnelle.

## 📁 Fichiers produits

| Fichier      | Rôle                             | Statut                                                 |
|--------------|----------------------------------|--------------------------------------------------------|
| `ca.key`     | Clé privée de la CA              | 🔴 **Secret absolu** — jamais partagé                  |
| `ca.crt`     | Certificat public de la CA       | 🟢 Public — à distribuer aux clients (dont l'ESP8266)  |
| `ca.srl`     | Numéro de série interne de la CA | ⚙️ Technique                                           |
| `server.key` | Clé privée du serveur            | 🔴 **Secret** — reste sur le serveur                   |
| `server.csr` | Demande de certificat            | 🟢 Public, devenu inutile une fois signé               |
| `server.crt` | Certificat signé du serveur      | 🟢 Public — utilisé avec `server.key` sur le serveur   |
| `san.ext`    | Détails techniques (nom, IP)     | ⚙️ Utilisé une seule fois, lors de la signature        |

## ⚙️ Paramètres retenus

| Paramètre                 | Valeur                                       |
|---------------------------|----------------------------------------------|
| Nom de la CA              | `Sentinel-X CA`                              |
| Nom du serveur (CN / SAN) | `sentinel-x.lan`                             |
| IP couverte (SAN)         | `192.168.10.1` — *à confirmer avec l'INFRA*  |
| Taille de clé CA          | 4096 bits                                    |
| Taille de clé serveur     | 2048 bits                                    |
| Algorithme de signature   | SHA-256                                      |
| Durée de validité         | 365 jours                                    |

## ⚠️ Points de vigilance

- **`ca.key` ne doit jamais se trouver dans un dépôt Git**, ni être transmis par un canal non chiffré.
- Le **nom et l'IP** du certificat sont à valider avec l'INFRA avant la configuration finale du service.
- **Validité des certificats** : 365 jours à partir de leur création — couvre la finale nationale du **17 novembre 2026**.

> [!TIP]
> Pour éviter tout commit accidentel des clés privées, ajouter au `.gitignore` :
> ```gitignore
> *.key
> ```

## ➡️ Prochaine étape

Utiliser `ca.crt`, `server.crt` et `server.key` pour configurer le chiffrement TLS du service retenu par l'équipe.
