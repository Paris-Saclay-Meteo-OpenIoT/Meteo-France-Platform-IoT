#!/usr/bin/env python3
"""
Wrapper pour synchroniser MongoDB → PostgreSQL avant d'exécuter le pipeline ML
Gère les données météorologiques et génère les prédictions
"""

import logging
import sys
import os
import asyncio
from mongo_to_postgres import main as sync_mongodb_to_postgres
from main import run_pipeline
from stations_config import get_target_stations, AVAILABLE_STATIONS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def run_full_pipeline(target_stations=None, region=None):
    """
    Exécute la synchronisation puis le pipeline ML
    
    Args:
        target_stations: Liste explicite des stations à traiter
        region: Région prédéfinie ('CORSE', 'PROVENCE_ALPES_AZUR', etc.)
    """
    # Déterminer les stations cibles
    # NOTE: Si pas de paramètres, on traite TOUTES les stations disponibles
    if region:
        target_stations = get_target_stations(region)
        logger.info(f"📍 Région sélectionnée: {region}")
    elif target_stations is None:
        # Par défaut: traiter TOUTES les stations (None = pas de filtrage)
        target_stations = None
        logger.info(f"📍 Pas de filtrage - Toutes les stations seront traitées")
    
    try:
        logger.info("█" * 80)
        logger.info("🌍 DÉMARRAGE DU PIPELINE MÉTÉOROLOGIQUE COMPLET")
        logger.info("█" * 80)
        if target_stations:
            logger.info(f"📍 Stations cibles ({len(target_stations)}):")
            for station in sorted(target_stations):
                station_id = AVAILABLE_STATIONS.get(station, 'N/A')
                logger.info(f"   • {station:15s} (ID: {station_id})")
        else:
            logger.info(f"📍 Traitement de TOUTES les stations disponibles")
        logger.info("█" * 80)
        
        # Étape 0: Récupération / mise à jour des données historiques via API DPClim
        # Exécuté à chaque changement de jour pour maintenir les données à jour
        api_token_clima = os.getenv("API_TOKEN_CLIMA")
        if api_token_clima:
            logger.info("\n")
            logger.info("▓" * 80)
            logger.info("📡 ÉTAPE 0: Mise à jour des données historiques DPClim")
            logger.info("▓" * 80)
            try:
                from fetch_historical_data import main_async
                from sqlalchemy import create_engine, text
                from config import DB_URI
                
                engine = create_engine(DB_URI)
                with engine.connect() as conn:
                    result = conn.execute(text(
                        "SELECT COUNT(*), MAX(date) FROM weather_data"
                    ))
                    row = result.fetchone()
                    count = row[0] if row else 0
                    max_date = row[1] if row else None
                engine.dispose()
                
                from datetime import datetime, timedelta
                now = datetime.utcnow()
                
                if count < 5000:
                    # Première exécution : récupérer 3 mois d'historique (suffisant pour le ML)
                    logger.info(f"   📊 Seulement {count} enregistrements en base"
                                " — lancement de la récupération historique (3 mois)")
                    asyncio.run(main_async(months=3))
                elif max_date and (now - max_date).total_seconds() > 24 * 3600:
                    # Données obsolètes : récupérer le dernier mois pour combler le gap
                    days_behind = (now - max_date).days
                    logger.info(f"   📊 {count} enregistrements, dernière donnée: {max_date.strftime('%Y-%m-%d %H:%M')}"
                                f" ({days_behind}j de retard) — mise à jour incrémentale")
                    asyncio.run(main_async(months=1))
                else:
                    logger.info(f"   ✅ {count} enregistrements, données à jour"
                                f" (dernière: {max_date.strftime('%Y-%m-%d %H:%M') if max_date else 'N/A'})")
            except Exception as e:
                logger.warning(f"   ⚠️ Récupération historique non-bloquante: {e}")
        else:
            logger.info("   ℹ️  API_TOKEN_CLIMA non défini — historique DPClim ignoré")
        
        # Étape 1: Synchronisation
        logger.info("\n")
        logger.info("▓" * 80)
        logger.info("🔄 ÉTAPE 1: Synchronisation MongoDB → PostgreSQL")
        logger.info("▓" * 80)
        try:
            sync_result = sync_mongodb_to_postgres()
            logger.info("✅ Synchronisation réussie")
            logger.info("▓" * 80)
        except Exception as e:
            logger.error(f"❌ Erreur synchronisation: {e}", exc_info=True)
            raise
        
        # Étape 2: Pipeline ML et prédictions
        logger.info("\n")
        logger.info("▓" * 80)
        logger.info("🤖 ÉTAPE 2: Exécution du Pipeline ML - Génération des prédictions")
        logger.info("▓" * 80)
        try:
            ml_result = run_pipeline(target_stations=target_stations)
            logger.info("✅ Pipeline ML réussi")
            logger.info("▓" * 80)
        except Exception as e:
            logger.error(f"❌ Erreur Pipeline ML: {e}", exc_info=True)
            raise
        
        # Résumé final
        logger.info("\n")
        logger.info("█" * 80)
        logger.info("🎉 ✅ PIPELINE COMPLET RÉUSSI AVEC SUCCÈS!")
        logger.info("█" * 80)
        logger.info("📊 Les prédictions sont maintenant disponibles:")
        logger.info("   • Table PostgreSQL: forecast_results")
        logger.info("   • Accessible via API backend: /api/station/forecast/*")
        logger.info("   • Affichage frontend: Dashboard des stations")
        logger.info("█" * 80)
        
    except Exception as e:
        logger.error("\n")
        logger.error("█" * 80)
        logger.error(f"💥 ERREUR CRITIQUE DANS LE PIPELINE COMPLET: {e}")
        logger.error("█" * 80)
        raise

if __name__ == "__main__":
    # Lire la région depuis une variable d'environnement si disponible
    region = os.getenv('ML_TARGET_REGION', None)
    
    logger.info(f"Région cible (env ML_TARGET_REGION): {region or 'Défaut (toutes les stations)'}")
    
    run_full_pipeline(region=region)
