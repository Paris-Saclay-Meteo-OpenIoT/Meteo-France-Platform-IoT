import requests
from datetime import datetime, timezone
import sys

"""
Test qui permet de prouver que le pipeline est bien actif au niveau des données.
On interroge l'API pour récupérer les datas de toutes les stations, puis on prends l'update la plus récente.
Compare la date obtenue avec celle d'aujourd'hui permet de checker que l'update se fait bien
Prouve qu'une data datant du jour à traverser tout la chaine producer, kafka, bdd, api sans blocage
"""

URL = "http://localhost:5000/api/station"

try:
    r = requests.get(URL)
    data = r.json()
    if not data:
        print("Base de données")
        sys.exit(1)

    # On prend la date la plus récente trouvée
    dates = [item.get('updatedAt', '') for item in data]
    dates.sort(reverse=True)
    most_recent = dates[0]
    
    # On récupère juste la Date dans la donnée
    last_date_str = most_recent.split('T')[0]
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    print(f"Dernière donnée dans la bdd: {most_recent}")
    print(f"Date d'aujourd'hui: {today_str}")
    
    if last_date_str == today_str:
        print("SUCCÈS : Le système possède des données du jour.")
        print("Le pipeline du projet est donc opérationnel et fonctionnel.")
    else:
        print("ERREUR: Les données datent d'un autre jour.")

except Exception as e:
    print(f"Erreur : {e}")