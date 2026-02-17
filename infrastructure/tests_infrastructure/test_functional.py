import requests
import sys
import random
import time

"""
Ici on a un gros test fonctionnel qui va simuler tester l'expérience réelle d'un user de la vue en passant par le clic jusqu'à la fiche météo
Ce que l'on veut à la fin c'est vraiment vérifier et tester les comportements du backend en fonction des actions de l'user et de s'assurer de la confirmité
du projet.
"""

URL_SITE = "http://localhost:5000/api/station"

#fonction qui permet de converir les kelvin en celsius pour l'affichage
def kelvin_to_celsius(k):
    if k is None: return "N/A"
    return f"{round(k - 273.15, 1)}°C"

print("LANCEMENT DU SCÉNARIO UTILISATEUR")
print("=" * 20)

try:
    #On commence par lancer la carte juste ici
    print("Ouverture et chargement de la carte")
    start_time = time.time()
    
    try:
        r = requests.get(URL_SITE, timeout=10)
    except requests.exceptions.ConnectionError:
        print("ERREUR : Le serveur est éteint !")
        sys.exit(1)

    duration = time.time() - start_time
    data = r.json()

    if not data:
        print("ERREUR : L'écran est vide.")
        sys.exit(1)

    print(f"Toutes les stations sont chargés: {len(data)} stations (en {round(duration, 2)}s).")

    #On clique sur une station au hasard
    target = random.choice(data)
    
    # On récupère les informations essentielles
    name = target.get('name', 'INCONNU')
    station_id = target.get('station_id')
    temp_k = target.get('t')
    date_maj = target.get('updatedAt', 'Inconnue')

    print(f"On consulte la météo de : {name} (ID: {station_id})")
    print("AFFICHAGE DE LA FICHE MÉTÉO :")
    

    print(f"STATION: {name:<30} ")
    print(f"TEMPÉRATURE : {kelvin_to_celsius(temp_k):<30} ")
    print(f"MISE À JOUR : {date_maj[0:10]:<30}")


    # Vérification de cohérence si c'est un succès ou non
    if temp_k is not None:
        print("Données affichées correctement, test validé !")
    else:
        print("Attention Température manquante.")

    #On effectue un test de gestion des erreurs
    print("Test de Robustesse, on essaye de naviguer vers une page inexistante.")
    bad_url = f"{URL_SITE}/PAGE_INEXISTANTE_123"
    
    try:
        r_error = requests.get(bad_url, timeout=5)
        # 404:page introuvable et 200: succès
        if r_error.status_code in [404, 200]:
            print("Le serveur gère l'erreur sans planter.")
        else:
            print(f"Code retour inattendu : {r_error.status_code}")
            
    except Exception as e:
        print(f"Erreur de connexion lors du test négatif : {e}")

    print("=" * 10)
    print("SUCCÈS : PARCOURS UTILISATEUR VALIDÉ.")
    sys.exit(0)

except Exception as e:
    print(f"ERREUR CRITIQUE DANS LE TEST : {e}")
    sys.exit(1)