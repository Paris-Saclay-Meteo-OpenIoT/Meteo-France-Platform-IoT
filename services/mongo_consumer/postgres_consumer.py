import os
import json
import time
import logging
from kafka import KafkaConsumer
import psycopg2
from psycopg2.extras import execute_values

# Configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "ter_kafka:9092")

# --- MODIFICATION ICI : ON ECOUTE LES DEUX TOPICS ---
TOPIC_NAMES = ["weather-verified", "weather-real-time"]
# ----------------------------------------------------

PG_USER = os.getenv("POSTGRES_USER", "admin")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
PG_DB = os.getenv("POSTGRES_DB", "weatherDB")
PG_HOST = os.getenv("POSTGRES_HOST", "ter_postgres")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

def connect_to_postgres():
    retries = 10
    while retries > 0:
        try:
            return psycopg2.connect(user=PG_USER, password=PG_PASSWORD, dbname=PG_DB, host=PG_HOST, port=PG_PORT)
        except Exception as e:
            logging.warning(f"Connexion DB échouée, nouvel essai... ({e})")
            time.sleep(5)
            retries -= 1
    exit(1)

def format_meteo_date(date_val):
    """Convertit les formats de date (CSV float ou ISO string) en SQL Timestamp."""
    if date_val is None: return None
    s = str(date_val)
    
    # Cas 1 : Format CSV nombre (ex: 2026020719.0)
    try:
        if len(s) >= 10 and s.replace('.','').isdigit(): 
            clean_num = str(int(float(s)))
            if len(clean_num) == 10:
                 return f"{clean_num[0:4]}-{clean_num[4:6]}-{clean_num[6:8]} {clean_num[8:10]}:00:00"
    except: pass

    # Cas 2 : Format ISO déjà propre (ex: "2026-02-08T19:24:07Z")
    # Postgres gère bien l'ISO 8601 nativement, on renvoie tel quel
    return date_val

def get_val(data, *keys):
    """Cherche la valeur (insensible à la casse)."""
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None

def insert_data(conn, data):
    try:
        cur = conn.cursor()
        
        # --- MAPPING ---
        sid = get_val(data, 'station_id', 'poste', 'num_poste', 'id')
        name = get_val(data, 'name', 'nom', 'nom_usuel')
        lat = get_val(data, 'lat', 'latitude')
        lon = get_val(data, 'lon', 'longitude')
        st_type = get_val(data, 'type', 'poste_type') # Ajout du type
        s_date = get_val(data, 'start_date', 'date_ouverture') # Ajout date ouverture
        
        raw_ref_time = get_val(data, 'reference_time', 'date')
        ref_time = format_meteo_date(raw_ref_time)
        
        valid_time = get_val(data, 'validity_time', 'date')
        if not valid_time: valid_time = ref_time
        else: valid_time = format_meteo_date(valid_time)

        # On chope tout ce qu'on peut
        temp = get_val(data, 't', 'temperature')
        dew = get_val(data, 'td', 'point_de_rosee')
        hum = get_val(data, 'u', 'humidite')
        wind_dir = get_val(data, 'dd', 'direction_vent')
        wind_speed = get_val(data, 'ff', 'force_vent')
        rain = get_val(data, 'rr_per', 'rr1', 'precipitations') 

        # --- SQL ---
        
        # Insertion STATION : C'est là que la magie opère !
        # Si on reçoit un NOM ou une LAT/LON, on met à jour la ligne existante (même si elle a été créée vide avant)
        cur.execute("""
            INSERT INTO stations (station_id, name, type, geo_id_insee, lat, lon, start_date)
            VALUES (%s, %s, %s, NULL, %s, %s, %s)
            ON CONFLICT (station_id) DO UPDATE 
            SET name = COALESCE(EXCLUDED.name, stations.name),
                type = COALESCE(EXCLUDED.type, stations.type),
                lat = COALESCE(EXCLUDED.lat, stations.lat),
                lon = COALESCE(EXCLUDED.lon, stations.lon),
                start_date = COALESCE(EXCLUDED.start_date, stations.start_date),
                updated_at = CURRENT_TIMESTAMP;
        """, (sid, name, st_type, lat, lon, s_date))

        # Insertion MESURE
        cur.execute("""
            INSERT INTO weather_measurements 
            (station_id, reference_time, insert_time, validity_time, t, td, u, dd, ff, rr_per)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
        """, (sid, ref_time, time.strftime('%Y-%m-%d %H:%M:%S'), valid_time, temp, dew, hum, wind_dir, wind_speed, rain))
        
        conn.commit()
        cur.close()

    except Exception as e:
        conn.rollback()
        # On ignore les erreurs de doublons classiques, on log les vrais soucis
        logging.error(f"Erreur SQL sur station {data.get('station_id', '?')} : {e}")
        pass

def main():
    conn = connect_to_postgres()
    # On écoute les DEUX topics
    consumer = KafkaConsumer(
        *TOPIC_NAMES,  # L'étoile déballe la liste des topics
        bootstrap_servers=KAFKA_BROKER, 
        auto_offset_reset='earliest', 
        group_id="postgres-consumer-group-v8", # V8 pour le V8 engine !
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    logging.info(f"Consumer V8 démarré. Écoute sur : {TOPIC_NAMES}")
    
    for message in consumer:
        packet = message.value
        
        # Cas 1 : Structure "Historique" (avec rows)
        rows = packet.get("rows", [])
        
        # Cas 2 : Structure "Temps Réel" (Station unique, pas de rows, données à la racine)
        # C'est ce format que tu vois dans ton navigateur !
        if not rows and "station_id" in packet:
            # On traite le paquet directement comme une ligne
            insert_data(conn, packet)
            logging.info(f"⚡ Donnée TEMPS RÉEL insérée pour {packet.get('name', packet.get('station_id'))}")
            continue

        # Traitement du Cas 1 (Historique)
        meta_original = {
            "station_id": packet.get("station_id"),
            "name": packet.get("name") or packet.get("NOM_USUEL"),
            "lat": packet.get("lat") or packet.get("LAT"),
            "lon": packet.get("lon") or packet.get("LON")
        }
        metadata = {k.lower(): v for k, v in meta_original.items() if v is not None}

        count = 0
        for row in rows:
            row_normalized = {k.lower(): v for k, v in row.items()}
            row_normalized.update(metadata)
            
            if 'station_id' not in row_normalized and 'poste' in row_normalized:
                row_normalized['station_id'] = row_normalized['poste']
                
            insert_data(conn, row_normalized)
            count += 1
            
        if count > 0:
            logging.info(f"📜 Données HISTORIQUE traitées pour {packet.get('station_id')} ({count} lignes)")

if __name__ == "__main__":
    main()