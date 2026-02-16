import pandas as pd
from sqlalchemy import create_engine, text
from config import DB_URI

engine = create_engine(DB_URI)

def get_weather_data():
    # -- Fix Mongo query => Postgres SQL query
    query = """
        SELECT 
            m.*, 
            s.lat,
            s.lon,
            s.name AS nom_usuel, 
            m.reference_time AS date
        FROM weather_measurements m
        JOIN stations s ON m.station_id = s.station_id
        ORDER BY m.reference_time DESC
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
        df.columns = [c.lower() for c in df.columns]
        return df

def save_predictions(df):
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS forecast_results (
                station TEXT,
                forecast_time TIMESTAMP,
                lat FLOAT,
                lon FLOAT,
                t_pred FLOAT,
                ff_pred FLOAT,
                rr1_pred FLOAT,
                PRIMARY KEY (station, forecast_time)
            );
        """))
        df.to_sql('temp_forecast', conn, if_exists='replace', index=False)
        upsert_query = text("""
            INSERT INTO forecast_results (station, forecast_time, lat, lon, t_pred, ff_pred, rr1_pred)
            SELECT station, forecast_time, lat, lon, t_pred, ff_pred, rr1_pred FROM temp_forecast
            ON CONFLICT (station, forecast_time) 
            DO UPDATE SET 
                t_pred = EXCLUDED.t_pred,
                ff_pred = EXCLUDED.ff_pred,
                rr1_pred = EXCLUDED.rr1_pred,
                lat = EXCLUDED.lat,
                lon = EXCLUDED.lon;
        """)
        conn.execute(upsert_query)
        conn.execute(text("DROP TABLE temp_forecast;"))
        conn.commit()
    print(f"✅ {len(df)} prévisions mises à jour.")