# Guide de Contribution

## Comment contribuer ?

### 1 Fork ou Branch

```bash
# Clone du repo
git clone https://github.com/Paris-Saclay-Meteo-OpenIoT/Meteo-France-Platform-IoT.git
cd Meteo-France-Platform-IoT
git checkout -b feature/ma-feature

```

### 2 Faire vos changements

```bash
git add .
git commit -m "feat: description courte"
git push origin feature/ma-feature
```

### 3 Créer une Pull Request

- Allez sur GitHub
- Cliquez "Create Pull Request"
- Décrivez vos changements
- Attendez la review

### 4 Lancer localement

```bash
./launch.sh
```

# 5. Ouvrez une Pull Request

---

## Process de Pull Request

### Création de la PR

1. **Titre** : Clair

   - `fix(backend): corriger la validation du JWT`
   - `fix stuff` ou `update`

2. **Description** :

### Mergement automatique en CI/CD

Une fois mergée dans `main` :

1. GitHub Actions lance lint + tests
2. Si réussi : Images Docker sont buildées et pushées à GHCR
3. Les images sont prêtes pour le déploiement en production


---

##  Ressources

- [Documentation du projet](./README.md)
- [Installation locale](./launch.sh)
- [Architectural overview](./README.md#-architecture-du-projet)
- [GitHub Issues](https://github.com/Paris-Saclay-Meteo-OpenIoT/Meteo-France-Platform-IoT/issues)

---