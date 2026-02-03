import httpx
import json
import logging
from kafka import KafkaProducer
import yaml
import os
from apscheduler.schedulers.blocking import BlockingScheduler
import hashlib
from prometheus_client import start_http_server, Counter, Histogram, Gauge

# Collect almost real-time weather alerts from the Vigilance API and publish them to Kafka
# API constraint : 60 requests per minute 
# 1 request retrieve all the alerts
# Collecting data every 30 minutes
# Request are shared between Meteo France APIs

# -------------------------------------------------------------------
# CONFIGURATION AND LOGGING
# -------------------------------------------------------------------

# Load configuration from YAML file
CONFIG_FILE = "config/config.yaml"

with open(CONFIG_FILE, "r") as file:
    config = yaml.safe_load(file)

VIGILANCE_API_URL = config["api_url"]
KAFKA_BROKER = config["kafka_broker"]
FETCH_TIMEOUT = config["fetch_timeout"]
API_TOKEN = os.getenv("API_TOKEN")
TOPIC_NAME = "weather-alerts"

# Kafka Producer loaded globally for scheduled tasks
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    key_serializer=lambda k: str(k).encode('utf-8')
)

# Local cache to avoid duplicate alerts
published_alerts = set()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# -------------------------------------------------------------------
# PROMETHEUS METRICS
# -------------------------------------------------------------------
# empty = container down, 0 = API is waiting, 1 = API is working
api_status = Gauge("api_status_vigilance", "Indique si l'API est active")

# Endpoint for Prometheus metrics
start_http_server(8002)
logging.info("Serveur Prometheus démarré sur le port 8002.")
# -------------------------------------------------------------------
# UTILITY FUNCTIONS
# -------------------------------------------------------------------

def fetch_vigilance_data():
    """ Fetches weather alerts from the Vigilance API. """
    headers = {
        "accept": "*/*", 
        "apikey": API_TOKEN 
    }

    try:
        response = httpx.get(VIGILANCE_API_URL, headers=headers, timeout=FETCH_TIMEOUT)
        response.raise_for_status()
        logging.info("Données de vigilance récupérées avec succès.")
        return response.json()
    except httpx.RequestError as e:
        logging.error(f"Erreur lors de la requête : {e}")
    except httpx.HTTPStatusError as e:
        logging.error(f"Statut HTTP invalide : {e}")
    return None

def generate_alert_key(alert):
    """
    Generate a unique key for an alert based on its attributes.
    """
    base_key = f"{alert.get('domain_name')}-{alert.get('hazard_name')}-{alert.get('risk_name')}-{alert.get('start_time')}"
    
    # Hash the description to avoid long keys - 8 characters should be enough
    description_hash = hashlib.md5(alert.get('description', '').encode('utf-8')).hexdigest()[:8]
    
    return f"{base_key}-{description_hash}"

def extract_notable_alerts(data):
    """
    Extracts notable alerts from the Vigilance API data.
    """
    notable_alerts = []

    for bloc in data.get("product", {}).get("text_bloc_items", []):
        for item in bloc.get("bloc_items", []):
            for text_item in item.get("text_items", []):
                hazard_name = text_item.get("hazard_name", "Inconnu")  # Get the hazard type
                for term in text_item.get("term_items", []):
                    if term.get("risk_name") in ["Vert", "Jaune","Orange", "Rouge"]:
                        # Combine bold text and regular text into a single description
                        description = " ".join(
                            [text.get("bold_text", "") + " " + " ".join(text.get("text", []))
                             for text in term.get("subdivision_text", [])]
                        )

                        alert = {
                            "domain_name": bloc.get("domain_name"),
                            "title": bloc.get("bloc_title"),
                            "risk_name": term.get("risk_name"),
                            "risk_color": term.get("risk_color"),
                            "risk_level": term.get("risk_level"),
                            "hazard_name": hazard_name,
                            "start_time": term.get("start_time"),
                            "end_time": term.get("end_time"),
                            "description": description,
                        }

                        # Generate a unique key for the alert
                        alert["alert_key"] = generate_alert_key(alert)

                        # Add the alert to the list
                        notable_alerts.append(alert)

    return notable_alerts

def publish_alerts_to_kafka(alerts):
    """ Publishes alerts to the Kafka topic. Avoids duplicates. """
    for alert in alerts:
        alert_key = alert["alert_key"]
        if alert_key not in published_alerts:  # Check if the alert has been published before
            producer.send(TOPIC_NAME, key=alert.get("domain_name", "unknown"), value=alert)
            logging.info(f"Alerte publiée : {json.dumps(alert, indent=2)}")
            published_alerts.add(alert_key)  # Add the alert key to the set
        else:
            logging.info(f"Alerte ignorée (déjà vue) : {alert_key}")

# -------------------------------------------------------------------
# MAIN LOGIC
# -------------------------------------------------------------------

def main():
    api_status.set(1) # API is working
    logging.info("Début de l'interrogation de l'API Vigilance.")
    vigilance_data = fetch_vigilance_data()

    if vigilance_data:
        logging.info("Extraction des alertes notables.")
        notable_alerts = extract_notable_alerts(vigilance_data)

        if notable_alerts:
            logging.info(f"{len(notable_alerts)} alertes notables trouvées. Publication dans Kafka.")
            publish_alerts_to_kafka(notable_alerts)
        else:
            logging.info("Aucune alerte notable trouvée.")

    logging.info("Traitement terminé.")
    api_status.set(0) # API is waiting

# -------------------------------------------------------------------
# SCHEDULER
# -------------------------------------------------------------------

def scheduled_task():
    main()

if __name__ == "__main__":
    scheduled_task()  # Run the task once at startup
    logging.info("Initialisation du scheduler.")
    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_task, 'interval', minutes=30) # Run the task at the specified interval
    logging.info("Scheduler démarré. Requête toutes les 30 minutes.")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Arrêt du scheduler.")
    finally:
        logging.info("Fermeture du producteur Kafka.")
        producer.close()
