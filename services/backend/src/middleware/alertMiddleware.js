const pool = require("../config/db");
const { getAlertKey } = require("../scripts/alertUtils");
const { getIo } = require("../config/socket");

const activeAlerts = new Map();

// Fonction utilitaire pour sauvegarder dans PostgreSQL
const persistAlertToPostgres = async (alertData) => {
  try {
    const query = `
      INSERT INTO system_alerts (alert_name, severity, status, description, container, received_at, alert_key)
      VALUES ($1, $2, $3, $4, $5, NOW(), $6)
    `;

    const alertName = alertData.labels?.alertname || "Alerte Inconnue";
    const severity = alertData.labels?.severity || "info";
    const container = alertData.labels?.container || "N/A";
    const description =
      alertData.annotations?.description || "Pas de description";
    const status = alertData.status;
    const key = alertData.key;

    await pool.query(query, [
      alertName,
      severity,
      status,
      description,
      container,
      key,
    ]);
  } catch (err) {
    console.error("Erreur sauvegarde SQL:", err);
  }
};

const processAlert = async (payload) => {
  console.log("Payload reçu :", JSON.stringify(payload, null, 2));
  const alerts = Array.isArray(payload.alerts) ? payload.alerts : [payload];
  const now = new Date();

  for (const alert of alerts) {
    const key = getAlertKey(alert);

    let incomingStatus = "active";
    if (alert.status && alert.status.toLowerCase() === "resolved") {
      incomingStatus = "resolved";
    }

    if (activeAlerts.has(key)) {
      let existingAlert = activeAlerts.get(key);

      if (incomingStatus === "resolved") {
        existingAlert.status = "resolved";
      } else if (existingAlert.status === "resolved") {
        existingAlert.status = "active";
        console.log(`Réactivation de l'alerte : ${key}`);
      } else {
        existingAlert.status = "active";
      }

      existingAlert.lastUpdated = now;
      activeAlerts.set(key, existingAlert);

      // On remplace Mongo par Postgres et Socket
      await persistAlertToPostgres(existingAlert); // Sauvegarde Historique
      getIo().emit("alertUpdate", existingAlert); // Mise à jour Dashboard Admin
    } else {
      const newAlert = {
        ...alert,
        key,
        firstReceived: now,
        lastUpdated: now,
        status: incomingStatus,
      };

      activeAlerts.set(key, newAlert);

      await persistAlertToPostgres(newAlert); // Sauvegarde Historique
      getIo().emit("alert", newAlert); // Mise à jour Dashboard Admin
    }
  }
};

const aVerifierThresholdMs = 2 * 60 * 1000;
const resolvedThresholdMs = 5 * 60 * 1000;

setInterval(async () => {
  const now = new Date();

  for (const [key, alert] of activeAlerts.entries()) {
    const elapsed = now - alert.lastUpdated;

    if (alert.status === "active") {
      let hasChanged = false;

      if (elapsed > resolvedThresholdMs) {
        alert.status = "resolved";
        hasChanged = true;
        console.log(`Alerte ${key} marquée comme "resolved" par inactivité.`);
      } else if (
        elapsed > aVerifierThresholdMs &&
        alert.status !== "a_verifier"
      ) {
        alert.status = "a_verifier";
        hasChanged = true;
        console.log(`Alerte ${key} passée à "a_verifier".`);
      }

      if (hasChanged) {
        await persistAlertToPostgres(alert);
        getIo().emit("alertUpdate", alert);

        // Si résolu, on peut éventuellement le retirer de la mémoire active si tu veux
        // activeAlerts.delete(key);
      }
    }
  }
}, 30000);

module.exports = { processAlert };
