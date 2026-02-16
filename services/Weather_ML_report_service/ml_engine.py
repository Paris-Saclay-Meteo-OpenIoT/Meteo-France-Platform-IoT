import pandas as pd
import numpy as np
import logging
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
PARIS_TZ = ZoneInfo('Europe/Paris')

def run_ml_pipeline(df, station_mapping=None, target_stations=None):
    """
    Exécute le pipeline ML pour générer des prédictions météorologiques
    
    Args:
        df: DataFrame avec les données météorologiques historiques
        station_mapping: Dictionnaire nom_usuel -> station_id (NUM_POSTE)
        target_stations: Liste des stations à traiter (None = toutes)
    
    Returns:
        DataFrame avec les prédictions (station, forecast_time, lat, lon, t_pred, ff_pred, rr1_pred)
    """
    logger.info("🔮 INITIALISATION DU MOTEUR DE PRÉDICTION ML")
    logger.info(f"   📊 Données d'entrée: {len(df)} enregistrements")
    
    df['date'] = pd.to_datetime(df['date'])
    
    # Ne supprimer que les lignes où les colonnes ESSENTIELLES sont nulles
    # (pas dd, n, vis etc. qui peuvent être absentes dans les données API)
    essential_cols = ['nom_usuel', 'date', 't', 'u', 'ff', 'rr1']
    existing_essential = [c for c in essential_cols if c in df.columns]
    df = df.dropna(subset=existing_essential).copy()
    
    if df.empty:
        logger.warning("⚠️  DataFrame VIDE après nettoyage, impossible d'exécuter le ML")
        return pd.DataFrame()
    
    logger.info(f"   ✓ Après nettoyage: {len(df)} enregistrements valides")
    
    required_cols = ['nom_usuel', 't', 'u', 'ff', 'rr1']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"   ❌ Colonnes manquantes: {missing_cols}")
        return pd.DataFrame()
    
    logger.info("   ✓ Toutes les colonnes requises présentes")
    
    # Filtrer par stations cibles si spécifiées
    if target_stations:
        logger.info(f"   🎯 Filtrage pour stations cibles: {target_stations}")
        df = df[df['nom_usuel'].isin(target_stations)]
        logger.info(f"   ✓ Filtré pour stations cibles: {len(df)} enregistrements")
        if df.empty:
            logger.warning("   ⚠️  Aucun enregistrement trouvé pour les stations cibles")
            return pd.DataFrame()
    
    # Déterminer la période historique à utiliser (5 ans si possible, sinon 1 an, sinon tout)
    now = datetime.now()
    min_date_5y = now - timedelta(days=5*365)
    min_date_1y = now - timedelta(days=365)
    if df['date'].min() <= min_date_5y:
        logger.info("⏳ Utilisation de l'historique sur 5 ans pour les prédictions")
        df = df[df['date'] >= min_date_5y].copy()
    elif df['date'].min() <= min_date_1y:
        logger.info("⏳ Utilisation de l'historique sur 1 an (pas assez de données pour 5 ans)")
        df = df[df['date'] >= min_date_1y].copy()
    else:
        logger.info("⏳ Utilisation de tout l'historique disponible (moins d'1 an de données)")
    
    le = LabelEncoder()
    df['SID'] = le.fit_transform(df['nom_usuel'])
    
    # Si lat/lon manquent, les ajouter avec des valeurs par défaut
    if 'lat' not in df.columns:
        df['lat'] = 0.0
    if 'lon' not in df.columns:
        df['lon'] = 0.0
    
    coords_map = df[['nom_usuel', 'lat', 'lon']].drop_duplicates().set_index('nom_usuel')
    features = ['SID', 't', 'u', 'ff']
    stations = df['nom_usuel'].unique()
    
    logger.info(f"\n🎯 STATIONS À TRAITER: {len(stations)}")
    for i, st in enumerate(stations, 1):
        logger.info(f"   {i}. {st}")
    
    # Calcul de la base de prédiction en heure française (Europe/Paris)
    # Le container tourne en UTC, mais les prédictions doivent correspondre au jour à venir en heure locale
    # - Si exécution autour de minuit (0h-1h CET) : prédictions pour le jour courant (00:00 → 23:00 CET)
    # - Si exécution en journée (startup) : prédictions pour le lendemain (00:00 → 23:00 CET)
    now_local = datetime.now(PARIS_TZ)
    if now_local.hour < 2:
        # Exécution planifiée autour de minuit → prédire pour le jour courant (heure locale)
        forecast_base_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Exécution en journée (startup) → prédire pour demain (heure locale)
        forecast_base_local = (now_local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Convertir en UTC naïf pour stockage PostgreSQL (TIMESTAMP WITHOUT TIMEZONE)
    forecast_base = forecast_base_local.astimezone(timezone.utc).replace(tzinfo=None)
    
    all_rows = []
    target_day = forecast_base_local.strftime('%A %d/%m/%Y')
    
    logger.info(f"\n⏰ Exécution à: {now_local.strftime('%H:%M')} (heure locale Paris)")
    logger.info(f"📅 Jour cible des prédictions: {target_day}")
    logger.info(f"📈 Plage: {forecast_base_local.strftime('%d/%m %H:%M')} → {(forecast_base_local + timedelta(hours=23)).strftime('%d/%m %H:%M')} CET (stocké en UTC: {forecast_base.strftime('%H:%M')} → {(forecast_base + timedelta(hours=23)).strftime('%H:%M')})")
    
    # Entrainer les modèles et générer les prédictions
    for target_col in ['t', 'ff', 'rr1']:
        logger.info(f"\n🤖 Entraînement du modèle pour: {target_col.upper()}")
        
        y = np.array([df[target_col].shift(-i).values for i in range(1, 25)]).T
        valid_idx = ~np.isnan(y).any(axis=1)
        X_train = df[valid_idx][features]
        y_train = y[valid_idx]
        
        logger.info(f"   📚 Ensemble d'entraînement: {len(X_train)} échantillons")
        
        try:
            model = RandomForestRegressor(n_estimators=50, n_jobs=-1, random_state=42)
            model.fit(X_train, y_train)
            logger.info("   ✅ Modèle entraîné avec succès (RandomForest 50 estimators)")
            
            # Générer les prédictions pour chaque station
            for station in stations:
                last_data = df[df['nom_usuel'] == station].sort_values('date').iloc[-1:]
                if last_data.empty:
                    continue
                    
                preds = model.predict(last_data[features])[0]
                # station_mapping mappe nom_usuel -> station_id (= NUM_POSTE pour les données réelles)
                station_id = station_mapping.get(station, station) if station_mapping else station
                
                for i, val in enumerate(preds):
                    forecast_time = forecast_base + timedelta(hours=i)  # 00:00 → 23:00 du jour cible
                    found = False
                    for row in all_rows:
                        if row['station'] == station_id and row['forecast_time'] == forecast_time:
                            row[f'{target_col.lower()}_pred'] = round(val, 2)
                            found = True
                            break
                    if not found:
                        all_rows.append({
                            'station': station_id,
                            'forecast_time': forecast_time,
                            'lat': coords_map.loc[station, 'lat'], 
                            'lon': coords_map.loc[station, 'lon'], 
                            f'{target_col.lower()}_pred': round(val, 2)
                        })
        except Exception as e:
            logger.error(f"   ❌ Erreur lors de l'entraînement du modèle {target_col}: {e}", exc_info=True)
    
    result_df = pd.DataFrame(all_rows)
    
    if result_df.empty:
        logger.warning("⚠️  Aucune prédiction générée!")
        logger.info("\n✅ Pipeline ML COMPLÉTÉ (sans prédictions)")
        return result_df
    
    logger.info(f"\n📊 RÉSUMÉ DES PRÉDICTIONS GÉNÉRÉES")
    logger.info(f"   ✓ Nombre total de prédictions: {len(result_df)}")
    logger.info(f"   ✓ Stations couvertes: {result_df['station'].nunique()}")
    logger.info(f"   ✓ Horizons de prédiction par station: {len(result_df) // max(1, result_df['station'].nunique())}")
    
    if not result_df.empty:
        logger.info("\n   📌 Échantillon de prédictions:")
        for _, row in result_df.head(3).iterrows():
            logger.info(f"      Station {row['station']}: T={row.get('t_pred', 'N/A')}°C, FF={row.get('ff_pred', 'N/A')}m/s, RR1={row.get('rr1_pred', 'N/A')}mm")
    
    logger.info("\n✅ Pipeline ML COMPLÉTÉ AVEC SUCCÈS")
    return result_df