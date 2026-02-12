const express = require("express");
const pool = require("../config/db");
const router = express.Router();

// ==========================================
// 🏗️ LA REQUÊTE UNIVERSELLE
// ==========================================
// 1. s.* => Prend TOUTES les colonnes de la station (nom, lat, lon...)
// 2. wm.* => Prend TOUTES les colonnes de la mesure (t, rr1, uv, sol, neige...)
// 3. LEFT JOIN LATERAL => Technique optimisée pour choper la DERNIÈRE mesure uniquement.

const BASE_QUERY = `
  SELECT s.*, wm.*
  FROM stations s
  LEFT JOIN LATERAL (
    SELECT * FROM weather_measurements m
    WHERE m.station_id = s.station_id
    ORDER BY m.reference_time DESC
    LIMIT 1
  ) wm ON true
`;

// ==========================================
// 1. ROUTES DE RECHERCHE (Avec TOUTES les données)
// ==========================================

// 🏙️ Route "City" : Recherche par nom
router.get("/city/:name", async (req, res) => {
  try {
    const cityName = req.params.name;
    // On concatène notre requête de base avec le filtre
    const query = `${BASE_QUERY} WHERE s.name ILIKE $1 ORDER BY s.name ASC LIMIT 50`;

    const { rows } = await pool.query(query, [`%${cityName}%`]);

    if (rows.length === 0) {
      return res
        .status(404)
        .json({ error: `Aucune station trouvée pour "${cityName}"` });
    }
    res.json(rows);
  } catch (error) {
    console.error("Erreur city:", error);
    res.status(500).json({ error: "Erreur serveur" });
  }
});

// 📮 Route par Code Postal (ex: "11" pour l'Aude)
router.get("/postal/:code", async (req, res) => {
  try {
    const codePostal = req.params.code;
    const query = `${BASE_QUERY} WHERE s.station_id LIKE $1 ORDER BY s.station_id ASC`;

    const { rows } = await pool.query(query, [`${codePostal}%`]);

    if (rows.length === 0)
      return res.status(404).json({ error: "Aucune station trouvée" });

    res.json(rows);
  } catch (error) {
    console.error("Erreur postal:", error);
    res.status(500).json({ error: "Erreur serveur" });
  }
});

// ==========================================
// 2. ROUTES HISTORIQUES (Graphiques)
// ==========================================
// Ici on garde SELECT * sur weather_measurements uniquement
// car pour un graphique, on a déjà les infos de la station (pas besoin de les répéter 500 fois)

// ⏳ Historique 24h (Toutes colonnes)
router.get("/history/24h/:stationId", async (req, res) => {
  try {
    const { stationId } = req.params;
    const query = `
      SELECT * FROM weather_measurements 
      WHERE station_id = $1 
      AND reference_time >= NOW() - INTERVAL '24 hours'
      ORDER BY reference_time ASC
    `;
    const { rows } = await pool.query(query, [stationId]);
    res.json(rows);
  } catch (error) {
    res.status(500).json({ error: "Erreur serveur" });
  }
});

// 📅 Historique par Jour précis (Toutes colonnes)
router.get("/history/day/:stationId/:date", async (req, res) => {
  try {
    const { stationId, date } = req.params;
    const startOfDay = `${date} 00:00:00`;
    const endOfDay = `${date} 23:59:59`;

    const query = `
      SELECT * FROM weather_measurements 
      WHERE station_id = $1 
      AND reference_time >= $2 
      AND reference_time <= $3
      ORDER BY reference_time ASC
    `;
    const { rows } = await pool.query(query, [stationId, startOfDay, endOfDay]);
    res.json(rows);
  } catch (error) {
    console.error("Erreur historique jour:", error);
    res.status(500).json({ error: "Erreur serveur" });
  }
});

// ==========================================
// 3. ROUTES GÉNÉRIQUES
// ==========================================

// 🌍 TOUTES les stations (Attention : Gros volume de données !)
router.get("/", async (req, res) => {
  try {
    const query = `${BASE_QUERY} ORDER BY s.station_id ASC`;
    const { rows } = await pool.query(query);
    res.json(rows);
  } catch (error) {
    console.error("Erreur all stations:", error);
    res.status(500).json({ error: "Erreur serveur" });
  }
});

// 🆔 Une seule station par ID (Avec TOUTES ses infos + météo)
router.get("/:stationId", async (req, res) => {
  try {
    const { stationId } = req.params;
    const query = `${BASE_QUERY} WHERE s.station_id = $1`;

    const { rows } = await pool.query(query, [stationId]);

    if (rows.length === 0)
      return res.status(404).json({ error: "Station non trouvée" });

    res.json(rows[0]);
  } catch (error) {
    console.error("Erreur station ID:", error);
    res.status(500).json({ error: "Erreur serveur" });
  }
});

router.get("/alerts", async (req, res) => {
  res.json([]);
});

module.exports = router;
