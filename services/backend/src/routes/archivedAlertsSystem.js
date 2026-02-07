const express = require("express");
const router = express.Router();
const pool = require("../config/db");

// Fetch all archived alerts
router.get("/", async (req, res) => {
  try {
    const query = `
      SELECT * FROM system_alerts 
      WHERE status = 'archived' 
      ORDER BY received_at DESC
    `;
    const { rows } = await pool.query(query);

    const formattedAlerts = rows.map((alert) => ({
      ...alert,
      key: alert.alert_key,
    }));

    res.status(200).json(formattedAlerts);
  } catch (err) {
    console.error(
      "Erreur lors de la récupération des alertes archivées :",
      err,
    );
    res.status(500).json({ error: "Erreur serveur" });
  }
});

module.exports = router;
