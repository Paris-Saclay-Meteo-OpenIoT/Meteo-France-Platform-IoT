"""
Configuration des stations météorologiques
Permet de cibler des régions spécifiques pour les prédictions
"""

import logging

logger = logging.getLogger(__name__)

# Stations disponibles dans la base de données (23 stations corses)
# Format: {nom_usuel: NUM_POSTE}
AVAILABLE_STATIONS = {
    'AJACCIO':                '20004002',
    'ALISTRO':                '20303002',
    'BASTIA':                 '20148001',
    'BOCOGNANO':              '20040004',
    'CALACUCCIA':             '20047006',
    'CALVI':                  '20050001',
    'CONCA':                  '20092001',
    'CORTE':                  '20096008',
    'FIGARI':                 '20114002',
    'ILE ROUSSE':             '20093002',
    'MARIGNANA':              '20154001',
    'MOCA-CROCE':             '20160001',
    'OLETTA':                 '20185003',
    'PIETRALBA':              '20223001',
    'PILA-CANALE':            '20232002',
    'QUENZA':                 '20254006',
    'QUERCITELLO':            '20255003',
    'RENNO':                  '20258001',
    'SAMPOLO':                '20268001',
    'SANTO PIETRO DI TENDA':  '20314006',
    'SARI D\'ORCINO':         '20270001',
    'SARTENE':                '20272004',
    'SOLENZARA':              '20342001',
}

# Groupes de stations par région
STATIONS_BY_REGION = {
    'CORSE': [
        'AJACCIO',
        'ALISTRO',
        'BASTIA',
        'BOCOGNANO',
        'CALACUCCIA',
        'CALVI',
        'CONCA',
        'CORTE',
        'FIGARI',
        'ILE ROUSSE',
        'MARIGNANA',
        'MOCA-CROCE',
        'OLETTA',
        'PIETRALBA',
        'PILA-CANALE',
        'QUENZA',
        'QUERCITELLO',
        'RENNO',
        'SAMPOLO',
        'SANTO PIETRO DI TENDA',
        'SARI D\'ORCINO',
        'SARTENE',
        'SOLENZARA',
    ],
}

def get_target_stations(region=None):
    """
    Récupère les stations cibles pour une région
    
    Args:
        region: Nom de la région (ex: 'CORSE') ou None pour toutes
    
    Returns:
        Liste des stations cibles
    """
    if region is None:
        # Retourner toutes les stations disponibles
        return list(AVAILABLE_STATIONS.keys())
    
    if region.upper() not in STATIONS_BY_REGION:
        logger.warning(f"Région '{region}' non reconnue. Régions disponibles: {list(STATIONS_BY_REGION.keys())}")
        return []
    
    stations = STATIONS_BY_REGION[region.upper()]
    logger.info(f"📍 Région sélectionnée: {region.upper()}")
    logger.info(f"   Stations cibles: {', '.join(stations)}")
    return stations

def list_available_regions():
    """Liste toutes les régions disponibles"""
    return list(STATIONS_BY_REGION.keys())

def validate_stations(stations_list):
    """Vérifie que les stations sont disponibles"""
    available = list(AVAILABLE_STATIONS.keys())
    invalid = [s for s in stations_list if s not in available]
    
    if invalid:
        logger.warning(f"⚠️  Stations non trouvées: {invalid}")
        logger.info(f"   Stations disponibles: {available}")
        return [s for s in stations_list if s in available]
    
    return stations_list

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("📍 Régions disponibles:")
    for region in list_available_regions():
        print(f"   - {region}")
    
    print("\n🎯 Exemple - Stations de Corse:")
    for station in get_target_stations('CORSE'):
        print(f"   - {station}")
