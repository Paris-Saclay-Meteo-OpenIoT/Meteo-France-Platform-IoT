# Permet de consommer des messages Kafka et de stocker et de faire des MAJ avec TTL des data dans une base Redis.
# Permet d'avoir une vrai utilisation des data en temps réel avec une expiration des data qui est possible.
import redis
from kafka import KafkaConsumer
import json
import os
import logging
import time

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPICS = os.getenv("KAFKA_TOPICS", "weather-real-time,weather-alerts").split(',')

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# -------------------------------------------------------------------
# UTILITY FUNCTIONS
# -------------------------------------------------------------------

def process_real_time_data(redis_client, data):
    """
    Process real-time weather data and save it to Redis.
    """
    try:
        station_id = data.get("station_id")
        validity_time = data.get("validity_time")

        if not station_id or not validity_time:
            logging.warning("[weather-real-time] Manquant : station_id ou validity_time, skipping...")
            return

        redis_key = f"station:real-time:{station_id}"
        redis_client.hset(redis_key, validity_time, json.dumps(data))
        redis_client.expire(redis_key, 3600)  # 1 hour TTL
        logging.info(f"[weather-real-time] Données sauvegardé pour la station : {station_id} (validity_time={validity_time}).")
        # Publier un événement via Redis Pub/Sub pour notifier le serveur de WebSocket
        redis_client.publish('data_updates', json.dumps(data))
    except Exception as e:
        logging.error(f"[weather-real-time] Echec message : {e}")


def process_alert_data(redis_client, data):
    """
    Process weather alerts and save them to Redis.
    """
    try:
        logging.info(f"[weather-alerts] Traitement de l'alerte : {data}")
        alert_key = data.get("alert_key")

        if not alert_key:
            logging.warning("[weather-alerts] alert_key manquante, skipping...")
            return

        redis_key = f"alert:{alert_key}"
        redis_client.set(redis_key, json.dumps(data), ex=86400)  # 24 hours TTL
        logging.info(f"[weather-alerts] Données d'alerte sauvegardé (alert_key={alert_key}).")
    except Exception as e:
        logging.error(f"[weather-alerts] Echec message : {e}")


def process_message(redis_client, topic, message):
    """
    Dispatch Kafka messages to the appropriate processor based on the topic.
    """
    try:
        # Need JSON format to process the message
        if message.value:
            data = json.loads(message.value)
            if topic == "weather-real-time":
                process_real_time_data(redis_client, data)
            elif topic == "weather-alerts":
                process_alert_data(redis_client, data)
            else:
                logging.warning(f"[{topic}] Topic inconnu, skipping...")
    except Exception as e:
        logging.error(f"[{topic}] Echec du traitement du message: {e}")

# -------------------------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------------------------

def main():
    # 1. Connexion Redis
    redis_client = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True
    )

    # 2. Connexion Kafka avec Retry Loop
    consumer = None
    retries = 20
    while retries > 0:
        try:
            logging.info(f"Tentative de connexion à Kafka ({KAFKA_BROKER})...")
            consumer = KafkaConsumer(
                *KAFKA_TOPICS,
                group_id="redis-consumer-group",
                bootstrap_servers=KAFKA_BROKER,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda m: m.decode('utf-8')
            )
            logging.info("Connexion Kafka réussie !")
            break
        except Exception as e:
            logging.warning(f"Kafka pas encore prêt ({e}). Nouvelle tentative dans 5s... ({retries} essais restants)")
            time.sleep(5)
            retries -= 1
    
    if not consumer:
        logging.error("Impossible de se connecter à Kafka après plusieurs tentatives.")
        exit(1)

    logging.info(f"En attente de messages sur les topics: {', '.join(KAFKA_TOPICS)}")

    # Process each Kafka message
    for message in consumer:
        process_message(redis_client, message.topic, message)

if __name__ == "__main__":
    main()