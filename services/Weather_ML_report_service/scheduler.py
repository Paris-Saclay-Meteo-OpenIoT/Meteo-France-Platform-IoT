import schedule
import time
import logging
import sys
from datetime import datetime, timedelta
from pipeline_complete import run_full_pipeline

# Configuration du logging avec output au console pour Docker
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def has_future_predictions():
    """Vérifie si des prédictions pour le jour à venir existent déjà en base"""
    try:
        from sqlalchemy import create_engine, text
        from config import DB_URI
        engine = create_engine(DB_URI)
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM forecast_results WHERE forecast_time >= NOW()"
            ))
            count = result.fetchone()[0]
        engine.dispose()
        logger.info(f"   📊 Prédictions futures en base: {count}")
        return count > 0
    except Exception as e:
        logger.warning(f"   ⚠️ Impossible de vérifier les prédictions existantes: {e}")
        return False

def job_wrapper():
    """Wrapper pour exécuter le pipeline complet avec gestion d'erreurs"""
    try:
        logger.info("="*80)
        logger.info("🚀 DÉMARRAGE DU PIPELINE COMPLET (Synchronisation + ML)")
        logger.info("="*80)
        run_full_pipeline()
        logger.info("="*80)
        logger.info("✅ PIPELINE COMPLET TERMINÉ AVEC SUCCÈS")
        logger.info("="*80)
    except Exception as e:
        logger.error("="*80)
        logger.error(f"❌ ERREUR CRITIQUE LORS DE L'EXÉCUTION DU PIPELINE: {e}")
        logger.error("="*80, exc_info=True)

# Planifier l'exécution quotidienne à 00:00
schedule.every().day.at("00:00").do(job_wrapper)

logger.info("="*80)
logger.info("📅 SCHEDULER MÉTÉO AI DÉMARRÉ")
logger.info("⏰ Prochaine exécution programmée à 00:00 (UTC+1)")
logger.info("="*80)

# Exécution au démarrage uniquement si aucune prédiction future n'existe
logger.info("🔍 Vérification des prédictions existantes au démarrage...")
if has_future_predictions():
    logger.info("✅ Des prédictions pour le jour à venir existent déjà — démarrage sans exécution du pipeline")
else:
    logger.info("🔄 Aucune prédiction future trouvée — EXÉCUTION IMMÉDIATE DU PIPELINE...")
    job_wrapper()

while True:
    try:
        schedule.run_pending()
        time.sleep(60)
    except Exception as e:
        logger.error(f"Erreur dans la boucle scheduler: {e}", exc_info=True)
        time.sleep(60)