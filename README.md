# Weather Data Platform

Plateforme de collecte, traitement, export et visualisation de données météorologiques, basée sur une architecture orientée microservices avec Kafka, FastAPI, Redis, MongoDB, Prometheus & Grafana.

---

## Sommaire

- [Installation rapide](#-installation-rapide)
- [Architecture du projet](#-architecture-du-projet)
- [Modules principaux](#-modules-principaux)
- [Contribuer](#-contribuer)
- [CI/CD GitHub Actions](#-cicd-github-actions)

---

## Installation rapide

### 1. Cloner et configurer

```bash
git clone https://github.com/Paris-Saclay-Meteo-OpenIoT/Meteo-France-Platform-IoT.git
cd Meteo-France-Platform-IoT
cp .env_template .env
```

**Important:** Éditez `.env` et remplacez les valeurs placeholder par vos clés API Meteo France

### 2. Lancer le projet

```bash
# Démarrer tous les services
./app.sh start

# Arrêter les services
./app.sh stop
```

Le script va:

- Vérifier que Docker est installé
- Nettoyer les ressources Docker inutilisées (`docker system prune`)
- Lancer les services en arrière-plan

### 3. Accéder aux services

- **Frontend**: http://localhost:3001
- **Backend API**: http://localhost:5000
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090

### Troubleshooting

```bash
# Voir les logs
docker-compose logs -f

# Redémarrer un service
docker-compose restart [service_name]

# Nettoyer complètement (supprime les volumes)
docker-compose down -v
```

## Architecture du projet

Voici l'architecture complète de notre application::

![Architecture du projet](architecture.png)

Structure :

```
services/
├── api_climatologique_producer/
├── api_observations_producer/
├── api_vigilance_producer/
├── mongo_consumer/
├── redis_consumer/
├── api_export/
├── backend/
└── frontend/
```

---

## Modules principaux

| Module                        | Description                                 |
| ----------------------------- | ------------------------------------------- |
| `api_observations_producer`   | Produit des données météo temps réel        |
| `api_climatologique_producer` | Gère les données historiques (climatologie) |
| `api_vigilance_producer`      | Produit des alertes météo                   |
| `mongo_consumer`              | Stocke les données dans MongoDB             |
| `redis_consumer`              | Publie les données en temps réel via Redis  |
| `api_export`                  | Permet d’exporter les données au format CSV |
| `backend`                     | API utilisateur, sécurisation, requêtes     |
| `frontend`                    | Interface de visualisation                  |

---

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour les instructions sur comment contribuer au projet (fork, branch, PR).

---

## CI/CD GitHub Actions

Chaque push sur la branche `main` déclenche :

- Build des images Docker
- Push vers GitHub Container Registry
- Déploiement automatique sur une VM via SSH
