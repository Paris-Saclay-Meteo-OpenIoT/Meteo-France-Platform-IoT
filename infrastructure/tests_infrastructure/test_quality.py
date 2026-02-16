import requests
import sys
import copy 

"""
C'est un test de qualité des données
On va vérifier justement qu'il y a une unicité c'est à dire pas de doublons et checker que les datas météos sont réalistes
avec par exemple pas de températures aberrantes.
"""

URL = "http://localhost:5000/api/station"
MIN_TEMP_KELVIN = 223
MAX_TEMP_KELVIN = 323

try:
    r = requests.get(URL, timeout=5)
    data = r.json()
    
    if not data:
        print("ERREUR : Pas de données.")
        sys.exit(1)

    #ajout d'un potentiel doublon pour verifier l'intégrité du test
    # data.append(data[0]) # On prend la 1ère station et on la recopie à la fin
    
    #ajout d'une température aberrante
    # data[1]['t'] = 1273.15 # 1000°C

    print(f"Stations récupérées : {len(data)}")

    #Vérifier si il y a des doublons
    ids = [s.get('station_id') for s in data if 'station_id' in s]
    unique_ids = set(ids) # set permet de supprimer les doublons
    
    count_total = len(ids)
    count_unique = len(unique_ids)
    
    print(f"Nombre d'IDs trouvés : {count_total}")
    print(f"Nombre d'IDs uniques : {count_unique}")
    
    if count_total != count_unique:
        diff = count_total - count_unique
        print(f"ÉCHEC : Il y a {diff} doublon(s) caché(s) dans la liste !")
        # boucle pour voir lequel est en double
        seen = set()
        for x in ids:
            if x in seen:
                print(f"ID {x} apparaît plusieurs fois.")
                break
            seen.add(x)
        has_error = True
    else:
        print("Unicité parfaite")
        has_error = False

    # On vérifie la cohérence des valeurs
    aberrations = 0
    
    for i, station in enumerate(data):
        temp = station.get('t')
        if temp is not None:
            if not (MIN_TEMP_KELVIN <= temp <= MAX_TEMP_KELVIN):
                print(f"Ligne {i} : Station '{station.get('name')}' affiche {temp} K (Impossible !)")
                aberrations += 1

    if aberrations > 0:
        print(f"ÉCHEC : {aberrations} valeurs aberrantes trouvées.")
        has_error = True
    else:
        print("Toutes les températures sont réalistes.")

    if has_error:
        print("Le test a detecté des erreurs")
        sys.exit(1)
    else:
        print("Données certifiées conformes.")
        sys.exit(0)

except Exception as e:
    print(f"ERREUR : {e}")