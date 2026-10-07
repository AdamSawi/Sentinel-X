# Cybersécurité

Ce dossier accueille les travaux de cybersécurité de l’équipe Sentinel-X :


La CA et le certificat serveur ont été générés et vérifiés avec succès (server.crt: OK). La chaîne de confiance est opérationnelle.
Fichiers produits
Fichier	Rôle	Statut
ca.key	Clé privée de la CA	Secret absolu — jamais partagé
ca.crt	Certificat public de la CA	Public — à distribuer aux clients (dont l'ESP8266)
ca.srl	Numéro de série interne de la CA	Technique
server.key	Clé privée du serveur	Secret — reste sur le serveur
server.csr	Demande de certificat	Public, devenu inutile une fois signé
server.crt	Certificat signé du serveur	Public — utilisé avec server.key sur le serveur
san.ext	Détails techniques (nom, IP)	Utilisé une seule fois, lors de la signature
Paramètres retenus
Paramètre	Valeur
Nom de la CA	Sentinel-X CA
Nom du serveur (CN / SAN)	sentinel-x.lan
IP couverte (SAN)	192.168.10.1 — à confirmer avec l'INFRA
Taille de clé CA	4096 bits
Taille de clé serveur	2048 bits
Algorithme de signature	SHA-256
Durée de validité	365 jours
