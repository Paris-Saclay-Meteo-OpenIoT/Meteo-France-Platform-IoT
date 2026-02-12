import os
import json
import time
import logging
from kafka import KafkaConsumer
import psycopg2
from psycopg2.extras import execute_values

# Configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "ter_kafka:9092")
TOPIC_NAMES = ["weather-verified", "weather-real-time"]
PG_USER = os.getenv("POSTGRES_USER", "admin")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
PG_DB = os.getenv("POSTGRES_DB", "weatherDB")
PG_HOST = os.getenv("POSTGRES_HOST", "ter_postgres")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# LISTE COMPLETE DES COLONNES (Basée sur ton init.sql)
ALL_MEASUREMENT_COLUMNS = [
    'rr1', 'qrr1', 'drr1', 'qdrr1', 'hneigef', 'qhneigef', 'neigetot', 'qneigetot',
    't', 'qt', 'td', 'qtd', 'tn', 'qtn', 'htn', 'qhtn', 'tx', 'qtx', 'htx', 'qhtx',
    'dg', 'qdg', 't10', 'qt10', 't20', 'qt20', 't50', 'qt50', 't100', 'qt100',
    'tnsol', 'qtnsol', 'tn50', 'qtn50', 'tchaussee', 'qtchaussee', 'tw', 'qtw',
    'pstat', 'qpstat', 'pmer', 'qpmer', 'geop', 'qgeop', 'pmermin', 'qpmermin',
    'ff', 'qff', 'dd', 'qdd', 'fxi', 'qfxi', 'dxi', 'qdxi', 'hxi', 'qhxi',
    'fxy', 'qfxy', 'dxy', 'qdxy', 'hxy', 'qhxy',
    'ff2', 'qff2', 'dd2', 'qdd2', 'fxi2', 'qfxi2', 'dxi2', 'qdxi2', 'hxi2', 'qhxi2',
    'fxi3s', 'qfxi3s', 'dxi3s', 'qdxi3s', 'hxi3s', 'qhxi3s',
    'u', 'qu', 'un', 'qun', 'hun', 'qhun', 'ux', 'qux', 'hux', 'qhux',
    'uabs', 'quabs', 'dhumi40', 'qdhumi40', 'dhumi80', 'qdhumi80', 'dhumec', 'qdhumec',
    'tsv', 'qtsv', 'enth', 'qenth', 'ins', 'qins', 'glo', 'qglo', 'dir', 'qdir',
    'dif', 'qdif', 'glo2', 'qglo2', 'uv', 'quv', 'infrar', 'qinfrar', 'uv_indice', 'quv_indice',
    'n', 'qn', 'nbas', 'qnbas', 'cl', 'qcl', 'cm', 'qcm', 'ch', 'qch',
    'n1', 'qn1', 'c1', 'qc1', 'b1', 'qb1', 'n2', 'qn2', 'c2', 'qc2', 'b2', 'qb2',
    'n3', 'qn3', 'b3', 'qb3', 'c3', 'qc3', 'n4', 'qn4', 'c4', 'qc4', 'b4', 'qb4',
    'ww', 'qww', 'vv', 'qvv', 'dvv200', 'qdvv200', 'w1', 'qw1', 'w2', 'qw2',
    'sol', 'qsol', 'solng', 'qsolng', 'tsneige', 'qtsneige', 'tubeneige', 'qtubeneige',
    'esneige', 'qesneige', 'hneigefi3', 'qhneigefi3', 'hneigefi1', 'qhneigefi1',
    'tmer', 'qtmer', 'vvmer', 'qvvmer', 'etatmer', 'qetatmer', 'dirhoule', 'qdirhoule',
    'tlagon', 'qtlagon', 'uv2', 'quv2', 'ins2', 'qins2', 'infrar2', 'qinfrar2',
    'dir2', 'qdir2', 'dif2', 'qdif2'
]

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
    if date_val is None: return None
    s = str(date_val)
    try:
        # Format CSV brut Météo France (YYYYMMDDHH)
        if len(s) >= 10 and s.replace('.','').isdigit(): 
            clean_num = str(int(float(s)))
            if len(clean_num) == 10:
                 return f"{clean_num[0:4]}-{clean_num[4:6]}-{clean_num[6:8]} {clean_num[8:10]}:00:00"
    except: pass
    return date_val 

def get_val(data, key_list):
    """Cherche une valeur parmi plusieurs clés possibles."""
    for key in key_list:
        if key in data and data[key] is not None:
            return data[key]
    return None

def insert_data(conn, data):
    try:
        cur = conn.cursor()
        
        # 1. Infos Station (Identifiants et Localisation)
        sid = get_val(data, ['station_id', 'poste', 'num_poste', 'id'])
        name = get_val(data, ['name', 'nom', 'nom_usuel'])
        lat = get_val(data, ['lat', 'latitude'])
        lon = get_val(data, ['lon', 'longitude'])
        alt = get_val(data, ['alt', 'altitude', 'altti'])
        
        # 2. Date de référence
        raw_ref_time = get_val(data, ['reference_time', 'date'])
        ref_time = format_meteo_date(raw_ref_time)
        
        if not sid or not ref_time:
            logging.warning("Donnée ignorée : pas d'ID ou de date.")
            return

        # A. Insertion/Mise à jour STATION
        cur.execute("""
            INSERT INTO stations (station_id, name, lat, lon, alt)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (station_id) DO UPDATE 
            SET name = COALESCE(EXCLUDED.name, stations.name),
                lat = COALESCE(EXCLUDED.lat, stations.lat),
                lon = COALESCE(EXCLUDED.lon, stations.lon),
                alt = COALESCE(EXCLUDED.alt, stations.alt),
                updated_at = CURRENT_TIMESTAMP;
        """, (sid, name, lat, lon, alt))

        # B. Insertion MESURES (Dynamique pour tout gérer)
        
        # Dictionnaire des valeurs à insérer
        values_dict = {}
        
        # Mapping manuel pour les cas où le nom JSON != nom SQL
        mappings = {
            'rr1': ['rr1', 'rr', 'precipitations', 'rr_per'], # rr_per devient rr1
            'pstat': ['pstat', 'pres', 'pression'],
            'pmer': ['pmer', 'pression_mer']
        }

        # On remplit le dictionnaire avec toutes les colonnes possibles
        for col in ALL_MEASUREMENT_COLUMNS:
            # Soit on a un mapping spécifique, soit on cherche le nom de la colonne
            keys_to_search = mappings.get(col, [col])
            values_dict[col] = get_val(data, keys_to_search)

        # Construction de la requête SQL dynamique
        columns = ['station_id', 'reference_time'] + list(values_dict.keys())
        placeholders = ['%s'] * len(columns)
        values = [sid, ref_time] + list(values_dict.values())
        
        sql = f"""
            INSERT INTO weather_measurements ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT (station_id, reference_time) DO NOTHING;
        """
        
        cur.execute(sql, values)
        conn.commit()
        cur.close()

    except Exception as e:
        conn.rollback()
        logging.error(f"Erreur SQL sur station {data.get('station_id', '?')} : {e}")

def main():
    conn = connect_to_postgres()
    consumer = KafkaConsumer(
        *TOPIC_NAMES,
        bootstrap_servers=KAFKA_BROKER, 
        auto_offset_reset='earliest', 
        group_id="postgres-consumer-group-full-v1", 
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    logging.info(f"Consumer Full Schema démarré.")
    
    for message in consumer:
        packet = message.value
        rows = packet.get("rows", [])
        
        if not rows and "station_id" in packet:
            insert_data(conn, packet)
            continue

        meta_original = {
            "station_id": packet.get("station_id"),
            "name": packet.get("name") or packet.get("NOM_USUEL"),
            "lat": packet.get("lat") or packet.get("LAT"),
            "lon": packet.get("lon") or packet.get("LON"),
            "alt": packet.get("alt") or packet.get("ALTTI")
        }
        # Nettoyage des None dans metadata pour ne pas écraser
        metadata = {k: v for k, v in meta_original.items() if v is not None}

        count = 0
        for row in rows:
            # On fusionne la ligne de donnée avec les métadonnées de la station
            row_normalized = {k.lower(): v for k, v in row.items()}
            row_normalized.update(metadata)
            
            # Gestion cas CSV 'poste'
            if 'station_id' not in row_normalized and 'poste' in row_normalized:
                row_normalized['station_id'] = row_normalized['poste']
            
            insert_data(conn, row_normalized)
            count += 1
            
        if count > 0:
            logging.info(f"Station {packet.get('station_id')} : {count} mesures traitées.")

if __name__ == "__main__":
    main()