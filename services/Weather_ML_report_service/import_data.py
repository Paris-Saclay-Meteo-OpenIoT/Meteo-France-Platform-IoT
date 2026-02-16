import pandas as pd
from sqlalchemy import create_engine
from config import DB_URI
#This file is just for testing purposes
engine = create_engine(DB_URI)

columns_to_keep = {
    'AAAAMMJJHH': 'date',
    'NOM_USUEL': 'nom_usuel',
    'T': 't',
    'U': 'u',
    'FF': 'ff',
    'RR1': 'rr1',
    'LAT': 'lat',
    'LON': 'lon'
}

print("⏳ Début de l'importation filtrée (Post-Septembre 2025)...")

chunks = pd.read_csv('meteo_master.csv', usecols=columns_to_keep.keys(), chunksize=100000)

first_chunk = True
for chunk in chunks:
    chunk = chunk.rename(columns=columns_to_keep)
    
    chunk['date'] = pd.to_datetime(chunk['date'], format='%Y%m%d%H')
    
    chunk = chunk[chunk['date'] >= '2025-09-01']
    
    if chunk.empty:
        continue

    mode = 'replace' if first_chunk else 'append'
    chunk.to_sql('weather_data', engine, if_exists=mode, index=False)
    
    print(f"✅ Bloc traité : {len(chunk)} lignes ajoutées (période valide).")
    first_chunk = False


print("🏁 Importation filtrée terminée !")
