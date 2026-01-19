import os
import json
import time
import logging
from kafka import KafkaConsumer
import psycopg2
from psycopg2.extras import execute_values

# Configuration Kafka
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "ter_kafka:9092")
TOPIC_NAME = "weather-verified"

# Configuration PostgreSQL
PG_USER = os.getenv("POSTGRES_USER", "admin")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
PG_DB = os.getenv("POSTGRES_DB", "weatherDB")
PG_HOST = os.getenv("POSTGRES_HOST", "ter_postgres")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")

# Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def connect_to_postgres():
    """Tente de se connecter à PostgreSQL avec plusieurs essais."""
    retries = 10
    while retries > 0:
        try:
            conn = psycopg2.connect(
                user=PG_USER,
                password=PG_PASSWORD,
                dbname=PG_DB,
                host=PG_HOST,
                port=PG_PORT
            )
            logging.info("Connexion à PostgreSQL réussie")
            return conn
        except Exception as e:
            logging.warning(f"Échec connexion PostgreSQL ({retries} restants): {e}")
            time.sleep(5)
            retries -= 1
    logging.error("Impossible de se connecter à PostgreSQL.")
    exit(1)

def insert_data(conn, data):
    """Insère ou met à jour la station, puis insère la mesure."""
    try:
        cur = conn.cursor()
        
        # 1. Insertion / Mise à jour de la STATION
        # On utilise ON CONFLICT pour ne rien faire si la station existe déjà (ou mettre à jour si besoin)
        station_query = """
            INSERT INTO stations (station_id, name, type, geo_id_insee, lat, lon, start_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (station_id) DO UPDATE 
            SET name = EXCLUDED.name, 
                updated_at = CURRENT_TIMESTAMP;
        """
        # Gestion lat/let (coquille possible dans la source)
        latitude = data.get('lat') if data.get('lat') is not None else data.get('let')
        
        station_values = (
            data.get('station_id'),
            data.get('name'),
            data.get('type'),
            data.get('geo_id_insee'),
            latitude,
            data.get('lon'),
            data.get('start_date')
        )
        cur.execute(station_query, station_values)

        # 2. Insertion de la MESURE MÉTÉO
        measure_query = """
            INSERT INTO weather_measurements 
            (station_id, reference_time, insert_time, validity_time, t, td, u, dd, ff, dxi10, fxi10, rr_per)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        measure_values = (
            data.get('station_id'),
            data.get('reference_time'),
            data.get('insert_time'),
            data.get('validity_time'),
            data.get('t'),
            data.get('td'),
            data.get('u'),
            data.get('dd'),
            data.get('ff'),
            data.get('dxi10'),
            data.get('fxi10'),
            data.get('rr_per')
        )
        cur.execute(measure_query, measure_values)
        
        conn.commit()
        cur.close()
        logging.info(f"Données insérées pour station {data.get('station_id')}")

    except Exception as e:
        conn.rollback()
        logging.error(f"Erreur SQL: {e}")

def main():
    conn = connect_to_postgres()
    
    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset='earliest',
        group_id="postgres-consumer-group",
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    logging.info(f"En attente de messages sur Kafka topic '{TOPIC_NAME}'...")

    for message in consumer:
        data = message.value
        insert_data(conn, data)

if __name__ == "__main__":
    main()