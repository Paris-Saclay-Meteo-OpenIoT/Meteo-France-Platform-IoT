import requests
import time
import concurrent.futures

"""
Le concept de ce test est de surcharger l'API avec un pic intense de requêtes 
et de connexions simultanées pour provoquer un embouteillage 
et suivre l'évolution de la latence via une sonde externe.
"""

URL = "http://localhost:5000/api/station"
NB_REQUETES = 2000           # Nombre total de requêtes à envoyer
UTILISATEURS_SIMULTANES = 20

print(f"Cible : {URL}")
print(f"Charge : {NB_REQUETES} requêtes avec {UTILISATEURS_SIMULTANES} utilisateurs simultanés")


# La fonction déployée pour simuler un utilisateur qui se connecte
def surcharge(i):
    try:
        # On ne cherche pas de mesure de temps précise ici, le but est de charger le serveur
        r = requests.get(URL, timeout=10)
        if r.status_code == 200:
            return "OK"
        else:
            return "ERREUR_HTTP"
    except Exception:
        return "ERREUR_CONNEXION"


start = time.time()
resultats = []

# On lance les requêtes en parallèle
with concurrent.futures.ThreadPoolExecutor(max_workers=UTILISATEURS_SIMULTANES) as executor:
    # On stocke les résultats pour faire les comptes à la fin
    resultats = list(executor.map(surcharge, range(NB_REQUETES)))

end = time.time()
duree = end - start


nb_ok = resultats.count("OK")
nb_erreurs = NB_REQUETES - nb_ok

print("-" * 10)
print(f"TEST TERMINÉE en {duree:.2f} secondes.")
print(f"Débit généré : {NB_REQUETES / duree:.0f} requêtes/seconde")
print(f"Succès : {nb_ok}")
print(f"Échecs : {nb_erreurs}")
print("-" * 10)