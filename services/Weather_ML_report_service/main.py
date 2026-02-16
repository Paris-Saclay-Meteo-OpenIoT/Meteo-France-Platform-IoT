import pandas as pd
import logging
from db_handler import get_weather_data, save_predictions, get_station_mapping
from ml_engine import run_ml_pipeline
from viz_engine import generate_global_maps, generate_station_charts
from notifier import send_personalized_email

logger = logging.getLogger(__name__)

def run_pipeline(target_stations=None):
    """
    Exécute le pipeline complet de prédiction météorologique
    
    Args:
        target_stations: Liste des stations à traiter (None = toutes)
    """
    logger.info("📥 CHARGEMENT DES DONNÉES")
    
    # Charger les données météorologiques
    logger.info("   📂 Récupération des données météorologiques de PostgreSQL...")
    df_brut = get_weather_data()
    logger.info(f"   ✓ {len(df_brut)} enregistrements chargés")
    
    # Récupérer le mapping entre nom_usuel et station_id
    logger.info("   🔗 Récupération du mapping stations...")
    station_mapping = get_station_mapping()
    logger.info(f"   ✓ Mapping trouvé pour {len(station_mapping)} stations:")
    for station_name, station_id in sorted(station_mapping.items()):
        logger.info(f"      - {station_name}: {station_id}")
    
    # Exécuter le pipeline ML
    logger.info("\n🚀 EXÉCUTION DU PIPELINE ML")
    df_forecast = run_ml_pipeline(df_brut, station_mapping, target_stations=target_stations)
    
    if df_forecast.empty:
        logger.warning("⚠️  Aucune prédiction générée!")
        return
    
    # Sauvegarder les prédictions
    logger.info("\n💾 SAUVEGARDE DES PRÉDICTIONS")
    logger.info("   📝 Écriture dans PostgreSQL (table: forecast_results)...")
    save_predictions(df_forecast)
    logger.info(f"   ✓ {len(df_forecast)} prédictions sauvegardées avec succès")
    
    # Charger les clients
    logger.info("\n📧 GÉNÉRATION DES RAPPORTS ET NOTIFICATIONS")
    try:
        customers = pd.read_csv('customers.csv')
        logger.info(f"   ✓ {len(customers)} clients chargés depuis customers.csv")
        
        # Générer les cartes globales
        logger.info("   🗺️  Génération des cartes météorologiques globales...")
        global_maps = generate_global_maps(df_forecast)
        logger.info("   ✓ Cartes globales générées")
        
        # Envoyer les notifications personnalisées par client
        for _, c in customers.iterrows():
            station_data_full = df_forecast[df_forecast['station'] == c['station_name']]
            
            if not station_data_full.empty:
                logger.info(f"   📨 Génération du rapport pour {c['name']} (station: {c['station_name']})...")
                
                charts = generate_station_charts(df_forecast, c['station_name'])
                send_personalized_email(
                    email=c['email'], 
                    name=c['name'], 
                    station=c['station_name'], 
                    stats_full=station_data_full, 
                    global_maps=global_maps, 
                    station_charts=charts
                )
                logger.info(f"   ✅ Email envoyé à {c['email']}")
            else:
                logger.warning(f"   ⚠️  Pas de données pour {c['station_name']}")
        
        logger.info("\n✅ NOTIFICATIONS ENVOYÉES AVEC SUCCÈS")
        
    except FileNotFoundError:
        logger.warning("   ⚠️  customers.csv non trouvé, notifications désactivées")
    except Exception as e:
        logger.error(f"   ❌ Erreur lors de l'envoi des notifications: {e}", exc_info=True)
    
    logger.info("\n" + "="*80)
    logger.info("✅ PIPELINE COMPLET TERMINÉ AVEC SUCCÈS")
    logger.info("="*80)

if __name__ == "__main__":
    run_pipeline()