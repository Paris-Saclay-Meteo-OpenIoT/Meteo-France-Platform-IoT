#!/usr/bin/env python3
"""
Script pour synchroniser les données de MongoDB (temps réel) vers PostgreSQL (source ML)
À exécuter manuellement ou via cron pour garder weather_data à jour
"""

import os
import pandas as pd
from pymongo import MongoClient
from sqlalchemy import create_engine, text
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration MongoDB
MONGO_USER = os.getenv("MONGO_INITDB_ROOT_USERNAME", "root")
MONGO_PASS = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "root")
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:27017/"
MONGO_DB = "weatherDB"
MONGO_COLLECTION = "weatherData"

# Configuration PostgreSQL
POSTGRES_USER = os.getenv("POSTGRES_USER", "weatherapp")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "your_postgres_password_here")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "ter_postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "meteo_db")  # ✅ VRAIE BASE

DB_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

def connect_mongodb():
    """Connexion à MongoDB avec retry"""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        logger.info("✅ Connexion MongoDB réussie")
        return client
    except Exception as e:
        logger.error(f"❌ Erreur connexion MongoDB: {e}")
        raise

def connect_postgres():
    """Connexion à PostgreSQL"""
    try:
        engine = create_engine(DB_URI)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Connexion PostgreSQL réussie")
        return engine
    except Exception as e:
        logger.error(f"❌ Erreur connexion PostgreSQL: {e}")
        raise

def create_weather_data_table(engine):
    """Crée la table weather_data si elle n'existe pas"""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS weather_data (
                id SERIAL PRIMARY KEY,
                nom_usuel VARCHAR(255),
                station_id VARCHAR(255),
                date TIMESTAMP,
                t FLOAT,
                u FLOAT,
                ff FLOAT,
                rr1 FLOAT,
                lat FLOAT,
                lon FLOAT,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(station_id, date)
            );
        """))
        conn.commit()
        logger.info("✅ Table weather_data prête")

def extract_mongo_data(mongo_client, limit=None):
    """Extrait les données de MongoDB"""
    try:
        db = mongo_client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        
        # Récupérer les dernières données (tri par date descendante)
        query = {}
        cursor = collection.find(query).sort("date", -1)
        
        if limit:
            cursor = cursor.limit(limit)
        
        data = list(cursor)
        logger.info(f"📊 {len(data)} documents extraits de MongoDB")
        
        return data
    except Exception as e:
        logger.error(f"❌ Erreur extraction MongoDB: {e}")
        return []

def _parse_climatologique_date(raw_date):
    """Parse le format numérique YYYYMMDDHH (float/int) en datetime"""
    try:
        s = str(int(raw_date))  # ex: "2025021512"
        return datetime.strptime(s, "%Y%m%d%H")
    except Exception:
        return None

def transform_mongo_to_postgres(mongo_data):
    """Transforme les documents MongoDB au format PostgreSQL.
    
    Gère deux formats :
      - Documents climatologiques avec champ 'rows' (principal)
      - Documents plats (observations, fallback)
    """
    records = []
    skipped_no_rows = 0
    skipped_filter = 0

    for doc in mongo_data:
        try:
            rows = doc.get('rows')
            
            if rows and isinstance(rows, list):
                # --- Format climatologique (imbriqué) ---
                root_station_id = doc.get('station_id')
                root_lat = doc.get('lat')
                root_lon = doc.get('lon')
                root_nom = doc.get('nom')

                for row in rows:
                    raw_t = row.get('T')
                    if raw_t is not None and raw_t > 100:
                        raw_t = round(raw_t - 273.15, 2)

                    raw_date = row.get('DATE')
                    parsed_date = _parse_climatologique_date(raw_date) if raw_date else None

                    record = {
                        'nom_usuel': row.get('NOM_USUEL') or root_nom,
                        'station_id': str(int(row.get('POSTE', 0))) if row.get('POSTE') else root_station_id,
                        'date': parsed_date,
                        't': raw_t,
                        'u': row.get('U'),
                        'ff': row.get('FF'),
                        'rr1': row.get('RR1'),
                        'lat': row.get('LAT') or root_lat,
                        'lon': row.get('LON') or root_lon,
                    }

                    if record['nom_usuel'] and record['date']:
                        records.append(record)
                    else:
                        skipped_filter += 1
            else:
                # --- Format plat (observations / fallback) ---
                raw_t = doc.get('t') or doc.get('T')
                if raw_t is not None and raw_t > 100:
                    raw_t = round(raw_t - 273.15, 2)

                raw_date = doc.get('date') or doc.get('DATE') or doc.get('reference_time')
                parsed_date = None
                if raw_date is not None:
                    if isinstance(raw_date, (int, float)) and raw_date > 2000000000:
                        parsed_date = _parse_climatologique_date(raw_date)
                    else:
                        try:
                            parsed_date = pd.to_datetime(raw_date)
                        except Exception:
                            parsed_date = None

                    # Filtrer les entrées non-horaires (infra-horaire)
                    if parsed_date and (parsed_date.second != 0 or parsed_date.microsecond != 0):
                        skipped_filter += 1
                        continue

                record = {
                    'nom_usuel': doc.get('nom_usuel') or doc.get('NOM_USUEL') or doc.get('name'),
                    'station_id': doc.get('station_id') or doc.get('STATION_ID'),
                    'date': parsed_date,
                    't': raw_t,
                    'u': doc.get('u') or doc.get('U'),
                    'ff': doc.get('ff') or doc.get('FF'),
                    'rr1': doc.get('rr1') or doc.get('RR1') or doc.get('rr_per'),
                    'lat': doc.get('lat') or doc.get('LAT'),
                    'lon': doc.get('lon') or doc.get('LON'),
                }

                if record['nom_usuel'] and record['date']:
                    records.append(record)
                else:
                    skipped_no_rows += 1
        except Exception as e:
            logger.warning(f"⚠️ Impossible de transformer document: {e}")
            continue

    logger.info(f"✅ {len(records)} documents transformés "
                f"({skipped_filter} filtrés, {skipped_no_rows} ignorés - champs manquants)")
    return records

def load_postgres_data(engine, records):
    """Insère les données dans PostgreSQL (avec UPSERT)"""
    if not records:
        logger.warning("⚠️ Aucune donnée à insérer")
        return 0
    
    try:
        df = pd.DataFrame(records)
        
        # Convertir les dates en datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Insérer avec UPSERT (ON CONFLICT)
        with engine.connect() as conn:
            # Utiliser copy_from pour performance
            for _, row in df.iterrows():
                conn.execute(text("""
                    INSERT INTO weather_data 
                    (nom_usuel, station_id, date, t, u, ff, rr1, lat, lon)
                    VALUES (:nom_usuel, :station_id, :date, :t, :u, :ff, :rr1, :lat, :lon)
                    ON CONFLICT (station_id, date) 
                    DO UPDATE SET 
                        t = COALESCE(EXCLUDED.t, weather_data.t),
                        u = COALESCE(EXCLUDED.u, weather_data.u),
                        ff = COALESCE(EXCLUDED.ff, weather_data.ff),
                        rr1 = COALESCE(EXCLUDED.rr1, weather_data.rr1),
                        nom_usuel = EXCLUDED.nom_usuel,
                        lat = EXCLUDED.lat,
                        lon = EXCLUDED.lon
                """), {
                    'nom_usuel': row['nom_usuel'],
                    'station_id': row['station_id'],
                    'date': row['date'],
                    't': row['t'],
                    'u': row['u'],
                    'ff': row['ff'],
                    'rr1': row['rr1'],
                    'lat': row['lat'],
                    'lon': row['lon']
                })
            conn.commit()
        
        logger.info(f"✅ {len(df)} enregistrements insérés/mis à jour dans PostgreSQL")
        return len(df)
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'insertion PostgreSQL: {e}")
        return 0

def main():
    """Exécute la synchronisation complète"""
    logger.info("="*60)
    logger.info("🔄 SYNCHRONISATION MONGODB → POSTGRESQL")
    logger.info("="*60)
    mongo_client = None
    postgres_engine = None
    try:
        # Connexions
        mongo_client = connect_mongodb()
        postgres_engine = connect_postgres()
        
        # Préparer PostgreSQL
        create_weather_data_table(postgres_engine)
        
        # ETL
        mongo_data = extract_mongo_data(mongo_client)
        if not mongo_data:
            logger.warning("⚠️ Aucune donnée MongoDB trouvée!")
            return
        
        records = transform_mongo_to_postgres(mongo_data)
        inserted = load_postgres_data(postgres_engine, records)
        
        logger.info("="*60)
        logger.info(f"✅ SYNCHRONISATION RÉUSSIE : {inserted} enregistrements")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"❌ ERREUR FATALE: {e}")
    finally:
        if mongo_client:
            mongo_client.close()

if __name__ == "__main__":
    main()
