require('dotenv').config();
const express = require('express');
const cors = require('cors');
const http = require('http'); // Pour créer un serveur HTTP

const userRoutes = require('./routes/userRoutes');
const redisRoutes = require('./routes/redisRoutes');
const adminRoutes = require('./routes/adminRoutes');
const accueilRoutes = require('./routes/accueilRoutes');
const alertRoutes = require('./routes/alertRoutes');
const activeAlertsRoutes = require('./routes/activeAlertSystem');
const archiveAlertRoutes = require('./routes/archiveAlertSystem');
const archivedAlertsRoutes = require('./routes/archivedAlertsSystem');
const stationRoutes = require('./routes/stationAlertRoutes');
const passwordRoutes = require('./routes/passwordRoutes');


const redisSubscriber = require('./config/redisPubSub');
const redisClient = require('./config/redis');
const { initSocket, getIo } = require('./config/socket');

const Station = require('./model/stationModel');
const Alert = require('./model/alertModel');
const StationHistory = require('./model/stationHistoryModel');

// Importer la connexion à MongoDB
require('./config/mongo');

// Importer la route de test MongoDB
const testMongoRoute = require('./routes/testMongo');

// Création de l'application Express
const app = express();
const PORT = process.env.PORT || 5000;

// Middleware pour gérer CORS : ici, on autorise toutes les origines
app.use(
  cors({
    origin: process.env.CORS_ORIGIN || "http://localhost:3001",
    credentials: true,
}));
// Middleware pour parser le JSON
app.use(express.json());

// Monter le routeur Redis sous /api/redis par exemple
app.use('/api/redis', redisRoutes);
// Intégration du routeur pour la gestion des utilisateurs
app.use('/api/users', userRoutes);
// Intégration du routeur pour l'administration
app.use('/api/admin', adminRoutes);
// Intégration du routeur pour la page d'accueil
app.use('/api/accueil', accueilRoutes);

app.use('/api/test-mongo', testMongoRoute);

app.use('/api/alert-webhook', alertRoutes); // Route grafana alertes
app.use('/api/alerts/archive', archiveAlertRoutes); // Archiver une alerte
app.use('/api/alerts/archived', archivedAlertsRoutes); // Récupérer les alertes archivées
app.use('/api/alerts', activeAlertsRoutes); // Récupérer les alertes actives

app.use('/api/station', stationRoutes); // Route pour les stations

app.use('/api/users', passwordRoutes); // Route pour la réinitialisation de mot de passe

// Création d'un serveur HTTP
const server = http.createServer(app);
initSocket(server);
const io = getIo(); // Récupérer l'instance de Socket.IO

// Gérer les connexions Socket.IO
io.on('connection', async (socket) => {
  console.log('Un client est connecté, id:', socket.id);
  
  // Récupérer les données initiales de Redis
  try {
    const keys = await redisClient.keys('*');
    console.log(`Clés trouvées dans Redis au moment de la connexion: ${keys}`);
    const stations = {};
    const alerts = {};
    for (const key of keys) {
      const type = await redisClient.type(key);
      let value;
      switch (type) {
        case 'string':
          try {
            value = JSON.parse(await redisClient.get(key));
          } catch (e) {
            value = await redisClient.get(key);
          }
          break;
        case 'list':
          value = await redisClient.lRange(key, 0, -1);
          break;
        case 'hash':
          value = await redisClient.hGetAll(key);
          break;
        case 'set':
          value = await redisClient.sMembers(key);
          break;
        case 'zset':
          value = await redisClient.zRangeWithScores(key, 0, -1);
          break;
        default:
          value = `Type ${type} non géré`;
      }
      // Séparer les alertes des stations en fonction du préfixe de la clé
      if (key.startsWith('alert:')) {
        alerts[key] = value;
      } else {
        stations[key] = value;
      }
    }
    console.log("Données initiales envoyées:", { stations, alerts });
    socket.emit('data_update', { stations, alerts });
  } catch (err) {
    console.error("Erreur lors de la récupération des données initiales:", err);
  }
  
  socket.on('disconnect', () => {
    console.log('Client déconnecté:', socket.id);
  });
});

// fonction qui stocke les données des stations et alertes dans MongoDB
async function saveData(key, data) {
  if (key.startsWith('alert:')) {
    // Traitement pour les alertes
    let alertData = data;
    if (typeof alertData === 'string') {
      try {
        alertData = JSON.parse(alertData);
      } catch (e) {
        console.error("Erreur lors du parsing de l'alerte:", e);
        return;
      }
    }
    if (alertData && alertData.alert_key) {
      await Alert.findOneAndUpdate(
        { alert_key: alertData.alert_key },
        alertData,
        { upsert: true, new: true }
      );
      console.log(`Alerte ${alertData.alert_key} sauvegardée dans MongoDB.`);
    } else {
      console.error('Données d\'alerte invalides pour la clé:', key);
    }
  } else if (key.startsWith('station:')) {
    // Traitement pour les stations
    let stationData;
    if (typeof data === 'object' && !data.station_id) {
      const values = Object.values(data);
      if (values.length > 0) {
        try {
          stationData = JSON.parse(values[0]);
        } catch (e) {
          console.error('Erreur lors du parsing du hash Redis pour la station:', e);
          stationData = {};
        }
      }
    } else {
      stationData = data.data || data;
    }
    if (stationData && stationData.station_id) {
      await Station.findOneAndUpdate(
        { station_id: stationData.station_id },
        stationData,
        { upsert: true, new: true }
      );
      console.log(`Station ${stationData.station_id} sauvegardée dans MongoDB.`);

      // Enregistrer cette mise à jour dans l'historique stationHistory
      const historyData = { ...stationData };
      await StationHistory.create(historyData);
      console.log(`Historique pour la station ${stationData.station_id} inséré.`);
    } else {
      console.error('Données de station invalides pour la clé:', key);
    }
  } else {
    console.error('Clé non reconnue:', key);
  }
}

// Abonnement au canal Redis "data_updates"
redisSubscriber.subscribe('data_updates', async (message) => {
  try {
    const data = JSON.parse(message);
    const key = data.key || 'station:default';
    await saveData(key, data);
    console.log(`Données sauvegardées pour la clé ${key}`);
    io.emit('data_update', data);
  } catch (e) {
    console.error("Erreur lors du parsing ou de la sauvegarde du message :", e);
    io.emit('data_update', message);
  }
});


server.listen(PORT, () => {
  console.log(`Serveur démarré sur le port ${PORT}`);
});




