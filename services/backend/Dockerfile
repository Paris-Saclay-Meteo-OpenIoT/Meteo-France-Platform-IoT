# Utiliser l'image Node.js officielle
FROM node:18

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
CMD ["npm", "start"]
