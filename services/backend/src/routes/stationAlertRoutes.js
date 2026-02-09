// routes/stationRoutes.js
const express = require("express");
const pool = require("../config/db");

const router = express.Router();

// route pour récupérer lh'istorique d'une station sur 24h
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

    if (rows.length === 0) {
      return res
        .status(404)
        .json({ error: "Aucune donnée historique trouvée pour ces 24 heures" });
    }

    res.json(rows);
  } catch (error) {
    console.error(
      "Erreur SQL lors de la récupération de l'historique sur 24h:",
      error,
    );
    res.status(500).json({ error: "Erreur serveur" });
  }
});

// route pour récupérer l'historique d'une station sur une journée donnée (format YYYY-MM-DD)
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

    if (rows.length === 0) {
      return res
        .status(404)
        .json({ error: "Aucune donnée historique trouvée pour cette date" });
    }
    res.json(rows);
  } catch (error) {
    console.error(
      "Erreur SQL lors de la récupération de l'historique jour:",
      error,
    );
    res.status(500).json({ error: "Erreur serveur" });
  }
});

// Route pour rechercher une station par son NOM et récupérer ses données météo
// Exemple : /stations/search/data/Ajaccio
router.get("/city/:name", async (req, res) => {
  try {
    const cityName = req.params.name;

    // 1. La requête SQL Magique
    // - ILIKE : Permet de chercher insensible à la casse (Ajaccio = AJACCIO)
    // - Les % : Permettent de trouver "AJACCIO-MILELLI" en tapant juste "Ajaccio"
    // - JOIN : On fusionne les infos de la station ET ses mesures
    const query = `
      SELECT 
        s.station_id, s.name, s.lat, s.lon, -- Infos Station
        w.reference_time, w.t, w.rr_per, w.ff, w.u -- Infos Météo
      FROM stations s
      LEFT JOIN weather_measurements w ON s.station_id = w.station_id
      WHERE s.name ILIKE $1
      ORDER BY w.reference_time DESC
      LIMIT 500; 
    `;

    // On ajoute les % pour dire "qui contient ce mot"
    const values = [`%${cityName}%`];

    const { rows } = await pool.query(query, values);

    if (rows.length === 0) {
      return res.status(404).json({
        error: `Aucune donnée trouvée pour une station contenant '${cityName}'`,
      });
    }

    // Petit bonus : On renvoie aussi le nombre de résultats trouvés
    res.json({
      count: rows.length,
      data: rows,
    });
  } catch (error) {
    console.error("Erreur recherche par nom:", error);
    res.status(500).json({ error: "Erreur serveur" });
  }
});

// route pour récupérer les stations d'une même ville par code postal
router.get("/postal/:code", async (req, res) => {
  try {
    const codePostal = req.params.code;

    // En SQL, le "commence par" se fait avec LIKE 'abc%'
    const query = "SELECT * FROM stations WHERE station_id LIKE $1";
    const values = [`${codePostal}%`];

    const { rows } = await pool.query(query, values);

    if (rows.length === 0) {
      return res
        .status(404)
        .json({ error: "Aucune station trouvée pour ce code postal" });
    }
    res.json(rows);
  } catch (error) {
    console.error("Erreur SQL postal:", error);
    res.status(500).json({ error: "Erreur serveur" });
  }
});

// route pour récupérer toutes les alertes (TEMPORAIREMENT DÉSACTIVÉ)
router.get("/alerts", async (req, res) => {
  // res.json([]); // Renvoie vide pour l'instant pour ne pas casser le front
  try {
    // Optionnel : Si tu veux garder le code prêt pour quand la table existera :
    // const { rows } = await pool.query('SELECT * FROM alerts');
    // res.json(rows);

    // Pour l'instant, on renvoie vide :
    res.json([]);
  } catch (error) {
    console.error("Erreur alertes:", error);
    res.status(500).json({ error: "Erreur serveur" });
  }
});

// route pour récupérer toutes les stations
router.get("/", async (req, res) => {
  try {
    const query = "SELECT * FROM stations ORDER BY station_id ASC";
    const { rows } = await pool.query(query);
    res.json(rows);
  } catch (error) {
    console.error("Erreur SQL all stations:", error);
    res.status(500).json({ error: "Erreur serveur" });
  }
});

// route pour récupérer une station par son identifiant
router.get("/:stationId", async (req, res) => {
  try {
    const { stationId } = req.params;

    const query = "SELECT * FROM stations WHERE station_id = $1";
    const { rows } = await pool.query(query, [stationId]);

    if (rows.length === 0) {
      return res.status(404).json({ error: "Station non trouvée" });
    }
    res.json(rows[0]);
  } catch (error) {
    console.error("Erreur SQL station ID:", error);
    res.status(500).json({ error: "Erreur serveur" });
  }
});

module.exports = router;
