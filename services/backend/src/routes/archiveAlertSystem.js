const express = require("express");
const router = express.Router();
const pool = require("../config/db");

router.post("/", async (req, res) => {
  const { key } = req.body; // Le front envoie la clé unique

  try {
    // On cherche l'alerte dans la table unique
    const findQuery = `
      SELECT * FROM system_alerts 
      WHERE alert_key = $1 
      ORDER BY received_at DESC 
      LIMIT 1
    `;

    const { rows } = await pool.query(findQuery, [key]);

    if (rows.length === 0) {
      return res.status(404).json({ message: "Alerte non trouvée" });
    }

    const alert = rows[0];

    // Vérification : On regarde si CETTE dernière alerte est bien résolue
    if (alert.status !== "resolved" && alert.status !== "a_verifier") {
      return res.status(400).json({
        message:
          "La dernière alerte reçue n'est pas résolue, impossible d'archiver.",
        currentState: alert.status,
      });
    }

    // Action : On archive TOUTES les lignes de cette clé ou seulement la dernière
    const updateQuery = `
      UPDATE system_alerts 
      SET status = 'archived' 
      WHERE alert_key = $1 
      RETURNING *
    `;

    const result = await pool.query(updateQuery, [key]);

    res.status(200).json(result.rows[0]);
  } catch (err) {
    console.error("Erreur lors de l'archivage de l'alerte :", err);
    res.status(500).json({ error: "Erreur serveur" });
  }
});

module.exports = router;
