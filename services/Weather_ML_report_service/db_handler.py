import pandas as pd
import logging
from sqlalchemy import create_engine, text
from config import DB_URI

logger = logging.getLogger(__name__)
engine = create_engine(DB_URI)

def get_weather_data():
    """Récupère toutes les données météorologiques depuis PostgreSQL"""
    logger.info("🔍 Requête des données météorologiques...")
    try:
        query = "SELECT * FROM weather_data ORDER BY date DESC"
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
            df.columns = [c.lower() for c in df.columns]
            logger.info(f"   ✓ {len(df)} enregistrements récupérés")
            if not df.empty:
                logger.info(f"   ✓ Colonnes disponibles: {', '.join(df.columns)}")
                logger.info(f"   ✓ Stations uniques: {df['nom_usuel'].nunique()}")
            return df
    except Exception as e:
        logger.error(f"   ❌ Erreur lors de la récupération des données: {e}", exc_info=True)
        return pd.DataFrame()

def get_station_mapping():
    """Créer un mapping entre nom_usuel (du ML) et station_id (de MongoDB)"""
    logger.info("🔗 Création du mapping stations...")
    try:
        query = """
            SELECT DISTINCT nom_usuel, station_id FROM weather_data 
            WHERE nom_usuel IS NOT NULL AND station_id IS NOT NULL
            ORDER BY nom_usuel
        """
        with engine.connect() as conn:
            result = pd.read_sql(text(query), conn)
            if result.empty:
                logger.warning("   ⚠️  Aucune station trouvée pour le mapping")
                return {}
            mapping = dict(zip(result['nom_usuel'], result['station_id']))
            logger.info(f"   ✓ Mapping créé avec {len(mapping)} stations:")
            for nom, sid in sorted(mapping.items()):
                logger.info(f"      - {nom:15s} → {sid}")
            return mapping
    except Exception as e:
        logger.error(f"   ❌ Erreur récupération mapping stations: {e}", exc_info=True)
        return {}

def save_predictions(df):
    """Sauvegarde les prédictions dans PostgreSQL avec upsert"""
    logger.info("💾 SAUVEGARDE DES PRÉDICTIONS DANS POSTGRESQL")
    
    if df.empty:
        logger.warning("   ⚠️  Aucune prédiction à sauvegarder")
        return
    
    logger.info(f"   📊 Nombre de prédictions: {len(df)}")
    logger.info(f"   🏘️  Nombre de stations: {df['station'].nunique()}")
    logger.info(f"   📅 Plage temporelle: {df['forecast_time'].min()} à {df['forecast_time'].max()}")
    
    try:
        with engine.connect() as conn:
            # Créer la table si elle n'existe pas
            logger.info("   📋 Vérification/création de la table forecast_results...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS forecast_results (
                    id SERIAL,
                    station VARCHAR(50),
                    station_id VARCHAR(50),
                    forecast_time TIMESTAMP,
                    forecast_date DATE,
                    lat FLOAT,
                    lon FLOAT,
                    t_pred FLOAT,
                    ff_pred FLOAT,
                    rr1_pred FLOAT,
                    u_pred FLOAT DEFAULT NULL,
                    model_version VARCHAR(50) DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(station, forecast_time)
                );
            """))
            
            # Sauvegarder les prédictions
            logger.info("   ⏳ Insertion des prédictions...")
            
            # Convertir les types numpy/Series en types Python natifs pour psycopg2
            df_clean = df.copy()
            for col in ['lat', 'lon', 't_pred', 'ff_pred', 'rr1_pred', 'u_pred']:
                if col in df_clean.columns:
                    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').astype(float)
            if 'station' in df_clean.columns:
                df_clean['station'] = df_clean['station'].astype(str)
            
            # Ajouter station_id (= station) et forecast_date si absents
            if 'station_id' not in df_clean.columns and 'station' in df_clean.columns:
                df_clean['station_id'] = df_clean['station']
            if 'forecast_date' not in df_clean.columns and 'forecast_time' in df_clean.columns:
                df_clean['forecast_date'] = pd.to_datetime(df_clean['forecast_time']).dt.date
            
            df_clean.to_sql('temp_forecast', conn, if_exists='replace', index=False)
            
            # Upsert (insert or update) - construire dynamiquement basé sur les colonnes nettoyées
            available_cols = df_clean.columns.tolist()
            columns_str = ', '.join(available_cols)
            select_str = ', '.join(available_cols)
            update_str = ', '.join([f"{col} = EXCLUDED.{col}" for col in available_cols if col not in ['station', 'forecast_time']])
            
            upsert_query = text(f"""
                INSERT INTO forecast_results ({columns_str})
                SELECT {select_str}
                FROM temp_forecast
                ON CONFLICT (station, forecast_time) 
                DO UPDATE SET {update_str};
            """)
            conn.execute(upsert_query)
            conn.execute(text("DROP TABLE temp_forecast;"))
            conn.commit()
            
            logger.info(f"   ✅ {len(df)} prédictions sauvegardées avec succès")
            
            # Vérifier le résultat
            logger.info("   📈 Vérification des données sauvegardées...")
            verify_query = text("SELECT COUNT(*) as count, COUNT(DISTINCT station) as stations FROM forecast_results")
            result = conn.execute(verify_query).fetchone()
            logger.info(f"      Total prédictions en BD: {result[0]}")
            logger.info(f"      Nombre de stations: {result[1]}")
            
    except Exception as e:
        logger.error(f"   ❌ Erreur lors de la sauvegarde: {e}", exc_info=True)
        raise