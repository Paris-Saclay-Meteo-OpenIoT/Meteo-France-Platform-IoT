// routes/stationRoutes.js
const express = require('express');
const Station = require('../model/stationModel');
const Alert = require('../model/alertModel');
const StationHistory = require('../model/stationHistoryModel');
const pool = require('../config/postgres');

const router = express.Router();

// route pour récupérer l'historique d'une station sur 24h
router.get('/history/24h/:stationId', async (req, res) => {
  try {
    const { stationId } = req.params;
    const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
    
    // Source principale : PostgreSQL (données DPClim complètes)
    const pgQuery = `
      SELECT station_id, nom_usuel AS name, lat, lon, date AS reference_time, t, u, ff, dd, rr1
      FROM weather_data
      WHERE station_id = $1 AND date >= $2
      ORDER BY date ASC
    `;
    const result = await pool.query(pgQuery, [stationId, twentyFourHoursAgo]);
    
    if (result.rows && result.rows.length > 0) {
      return res.json(result.rows);
    }
    
    // Fallback MongoDB (observations temps réel — températures en Kelvin)
    const history = await StationHistory.find({
      station_id: stationId,
      reference_time: { $gte: twentyFourHoursAgo }
    }).sort({ reference_time: 1 });
    
    if (history && history.length > 0) {
      const converted = history.map(h => {
        const obj = h.toObject ? h.toObject() : { ...h };
        if (obj.t != null && obj.t > 100) obj.t = parseFloat((obj.t - 273.15).toFixed(2));
        return obj;
      });
      return res.json(converted);
    }
    
    return res.status(404).json({ error: 'Aucune donnée historique trouvée pour ces 24 heures' });
  } catch (error) {
    console.error("Erreur lors de la récupération de l'historique sur 24h:", error);
    res.status(500).json({ error: "Erreur serveur lors de la récupération de l'historique" });
  }
});

// route pour récupérer l'historique d'une station sur 7 jours
router.get('/history/7d/:stationId', async (req, res) => {
  try {
    const { stationId } = req.params;
    const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    
    // Source principale : PostgreSQL (données DPClim complètes)
    const pgQuery = `
      SELECT station_id, nom_usuel AS name, lat, lon, date AS reference_time, t, u, ff, dd, rr1
      FROM weather_data
      WHERE station_id = $1 AND date >= $2
      ORDER BY date ASC
    `;
    const result = await pool.query(pgQuery, [stationId, sevenDaysAgo]);
    
    if (result.rows && result.rows.length > 0) {
      return res.json(result.rows);
    }
    
    // Fallback MongoDB (observations temps réel — températures en Kelvin)
    const mongoHistory = await StationHistory.find({
      station_id: stationId,
      reference_time: { $gte: sevenDaysAgo }
    }).sort({ reference_time: 1 });
    
    if (mongoHistory && mongoHistory.length > 0) {
      const converted = mongoHistory.map(h => {
        const obj = h.toObject ? h.toObject() : { ...h };
        if (obj.t != null && obj.t > 100) obj.t = parseFloat((obj.t - 273.15).toFixed(2));
        return obj;
      });
      return res.json(converted);
    }
    
    return res.status(404).json({ error: 'Aucune donnée historique trouvée pour les 7 derniers jours' });
  } catch (error) {
    console.error("Erreur lors de la récupération de l'historique sur 7j:", error);
    res.status(500).json({ error: "Erreur serveur lors de la récupération de l'historique" });
  }
});

// route pour récupérer l'historique d'une station sur une journée donnée (format YYYY-MM-DD)
router.get('/history/day/:stationId/:date', async (req, res) => {
  try {
    const { stationId, date } = req.params;
    const startOfDay = new Date(date + 'T00:00:00Z');
    const endOfDay = new Date(date + 'T23:59:59.999Z');
    
    // Source principale : PostgreSQL (données DPClim complètes)
    const pgQuery = `
      SELECT station_id, nom_usuel AS name, lat, lon, date AS reference_time, t, u, ff, dd, rr1
      FROM weather_data
      WHERE station_id = $1 AND date >= $2 AND date <= $3
      ORDER BY date ASC
    `;
    const result = await pool.query(pgQuery, [stationId, startOfDay, endOfDay]);
    
    if (result.rows && result.rows.length > 0) {
      return res.json(result.rows);
    }
    
    // Fallback MongoDB (observations temps réel — températures en Kelvin)
    const history = await StationHistory.find({
      station_id: stationId,
      reference_time: { $gte: startOfDay, $lte: endOfDay }
    }).sort({ reference_time: 1 });
    
    if (history && history.length > 0) {
      const converted = history.map(h => {
        const obj = h.toObject ? h.toObject() : { ...h };
        if (obj.t != null && obj.t > 100) obj.t = parseFloat((obj.t - 273.15).toFixed(2));
        return obj;
      });
      return res.json(converted);
    }
    
    return res.status(404).json({ error: 'Aucune donnée historique trouvée pour cette date' });
  } catch (error) {
    console.error("Erreur lors de la récupération de l'historique pour la date donnée:", error);
    res.status(500).json({ error: "Erreur serveur lors de la récupération de l'historique" });
  }
});

// route pour récupérer une station par son identifiant
router.get('/:stationId', async (req, res) => {
    try {
      const stationId = req.params.stationId;
      
      // Chercher dans MongoDB d'abord
      let station = await Station.findOne({ station_id: stationId });
      
      // Si pas trouvée dans MongoDB, chercher dans PostgreSQL
      if (!station) {
        const pgQuery = `
          SELECT DISTINCT station_id, nom_usuel, lat, lon 
          FROM weather_data 
          WHERE station_id = $1 
          LIMIT 1
        `;
        const result = await pool.query(pgQuery, [stationId]);
        
        if (result.rows && result.rows.length > 0) {
          const row = result.rows[0];
          station = {
            station_id: row.station_id,
            name: row.nom_usuel,
            lat: row.lat,
            lon: row.lon
          };
        }
      }
      
      if (!station) {
        return res.status(404).json({ error: 'Station non trouvée pour cet identifiant' });
      }
      res.json(station);
    } catch (error) {
      console.error('Erreur lors de la récupération de la station:', error);
      res.status(500).json({ error: 'Erreur serveur lors de la récupération de la station' });
    }
  });

// route pour récupérer les stations d'une même ville par code postal
router.get('/postal/:code', async (req, res) => {
  try {
    const codePostal = req.params.code;
    // On utilise une expression régulière pour trouver les station_id qui commencent par le code postal
    const stations = await Station.find({
      station_id: { $regex: `^${codePostal}` }
    });
    if (!stations || stations.length === 0) {
      return res.status(404).json({ error: 'Aucune station trouvée pour ce code postal' });
    }
    res.json(stations);
  } catch (error) {
    console.error('Erreur lors de la récupération des stations par code postal:', error);
    res.status(500).json({ error: 'Erreur serveur lors de la récupération des stations' });
  }
});


// route pour récupérer toutes les alertes
router.get('/alerts', async (req, res) => {
    try {
      const alerts = await Alert.find({});
      res.json(alerts);
    } catch (error) {
      console.error('Erreur lors de la récupération des alertes:', error);
      res.status(500).json({ error: 'Erreur serveur lors de la récupération des alertes' });
    }
});

// route pour récupérer toutes les stations
router.get('/', async (req, res) => {
  try {
    // Chercher dans MongoDB d'abord
    let stations = await Station.find({});
    
    // Si aucune dans MongoDB, chercher dans PostgreSQL
    if (!stations || stations.length === 0) {
      const pgQuery = `
        SELECT DISTINCT station_id, nom_usuel, lat, lon 
        FROM weather_data 
        ORDER BY station_id
      `;
      const result = await pool.query(pgQuery);
      
      if (result.rows && result.rows.length > 0) {
        stations = result.rows.map(row => ({
          station_id: row.station_id,
          name: row.nom_usuel,
          lat: row.lat,
          lon: row.lon
        }));
      }
    }
    
    res.json(stations);
  } catch (error) {
    console.error('Erreur lors de la récupération des stations:', error);
    res.status(500).json({ error: 'Erreur lors de la récupération des stations' });
  }
});

// route pour récupérer les prédictions d'une station sur 24h (jour à venir)
router.get('/forecast/24h/:stationId', async (req, res) => {
  try {
    const { stationId } = req.params;
    const now = new Date();
    
    // Récupérer les 24 prochaines prédictions disponibles à partir de maintenant
    const query = `
      SELECT station, forecast_time, lat, lon, t_pred, ff_pred, rr1_pred, u_pred
      FROM forecast_results
      WHERE station = $1 AND forecast_time >= $2
      ORDER BY forecast_time ASC
      LIMIT 24
    `;
    
    const result = await pool.query(query, [stationId, now]);
    
    if (!result.rows || result.rows.length === 0) {
      return res.status(404).json({ error: 'Aucune prédiction disponible pour les 24 prochaines heures' });
    }
    
    res.json(result.rows);
  } catch (error) {
    console.error("Erreur lors de la récupération des prédictions sur 24h:", error);
    res.status(500).json({ error: "Erreur serveur lors de la récupération des prédictions" });
  }
});

module.exports = router;
