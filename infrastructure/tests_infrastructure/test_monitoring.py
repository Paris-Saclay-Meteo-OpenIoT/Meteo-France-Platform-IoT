import requests
import time
import datetime


"""
Ce test permet de mesurer la qualité de service du projet en temps réel dans un premier je l'ai utilisé pour tester la répartition des 
BDD sur le projet que ce soit pour Redis ou MongoDB
Il permet aussi de détecter:
1. Les pannes franches (Crash BDD / Arrêt conteneur) qui provoque un échec total
2. La dégradation de performance et donc là on aura le système qui est en surcharge
3. Le retour à la normale avec notre principe de "auto-guérison" et là on aura un simple "OK"
"""

URL = "http://localhost:5000/api/station"

print(f"TEST DU MONITORING SUR {URL}")
print("Appuyez sur CTRL+C pour arrêter le test.")
print("-" * 10)

try:
    while True: # Boucle infinie
        start = time.time()
        try:
            # On laisse 10 secondes au serveur pour répondre (pour ne pas faire "Echec" trop vite)
            r = requests.get(URL, timeout=10)
            duree = (time.time() - start) * 1000
            
            heure = datetime.datetime.now().strftime("%H:%M:%S")
            
            if r.status_code == 200:
                if duree > 1000:
                    print(f"[{heure}]  LE SERVEUR SOUFFRE - Latence : {duree:.0f}ms")
                else:
                    print(f"[{heure}] OK - Réponse fluide en {duree:.0f}ms")
            else:
                print(f"[{heure}]  ERREUR HTTP {r.status_code}")
                
        except Exception as e:
            heure = datetime.datetime.now().strftime("%H:%M:%S")
            # Si ça dépasse 10 secondes ou que la connexion coupe
            print(f"[{heure}] ECHEC TOTAL - Serveur inaccessible ({e})")

        time.sleep(0.5) # Une requête toutes les demi-secondes

except KeyboardInterrupt:
    print("\nTest arrêté par l'utilisateur.")