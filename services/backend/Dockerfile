# Utiliser l'image Node.js officielle
FROM node:18

# Installer bash (optionnel, utile pour exec bash dans le conteneur)
RUN apt-get update && apt-get install -y bash && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /usr/src/app

# Copier les fichiers nécessaires
COPY package*.json ./

# Installer les dépendances
RUN npm install

# Copier le reste des fichiers
COPY . .

# Exposer le port pour le serveur
EXPOSE 5000

# Commande de démarrage
CMD ["npx", "nodemon", "src/app.js"]
