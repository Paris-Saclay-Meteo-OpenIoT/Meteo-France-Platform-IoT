import requests
import json
import sys
"""
Test qui permet de garantir que les datas renvoyées par l'API respectent le bon format
pour que le front ne plante pas s'il essaye de les lire.
On va vérifier la réponse en espérant du JSON valide et non une erreur.
Il va inspecter le premier objet reçu pour lister les clés et confirmer que les champs que l'on attend
sont bien présent.
"""

URL = "http://localhost:5000/api/station"


# Liste des clés attendues, si une seule de ces clés manque, le test échouera.
REQUIRED_KEYS = ["station_id", "name", "t", "lon", "updatedAt"]

print(f"Vérification des clés vitales : {REQUIRED_KEYS}")

try:
    #On interroge l'API
    try:
        r = requests.get(URL, timeout=5)
    except requests.exceptions.ConnectionError:
        print("ERREUR: L'API est injoignable (Connection Refused).")
        sys.exit(1)

    if r.status_code != 200:
        print(f"ERREUR API: Code {r.status_code}")
        sys.exit(1)
        
    data = r.json()
    
    #On check qu'on a bien des données
    if not data:
        print("ERREUR : La base de données est vide.")
        sys.exit(1)
        
    station = data[0] # On analyse le premier objet
    
    #On fait une vérification des clés
    missing_keys = []
    for key in REQUIRED_KEYS:
        if key not in station:
            missing_keys.append(key)
            
    if missing_keys:
        print(f"ÉCHEC : Structure invalide !")
        print(f"Clés manquantes : {missing_keys}")
        sys.exit(1)
    else:
        print("SUCCÈS : Toutes les clés obligatoires sont présentes.")
        print(f"Exemple de Station : {station.get('name')} (ID: {station.get('station_id')})")
        sys.exit(0)

except Exception as e:
    print(f"ERREUR IMPRÉVUE : {e}")
    sys.exit(1)