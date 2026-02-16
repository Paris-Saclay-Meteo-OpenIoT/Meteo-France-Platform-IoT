import os
import subprocess
import sys
import time

"""
Dans ce code, on retrouve le scénario de test global qui teste tout notre pipeline.
Il va exécuter toute notre suite de tests en utilisant la logique de Fail-Fast: 
en commençant par l'audit des données brutes, puis le parcours utilisateur, la vérification du monitoring, 
pour finir par un crash test du serveur sous haute charge surveillé par une sonde en arrière-plan.
Ce que l'on veut à la fin, c'est valider la robustesse de bout en bout de notre architecture (Data, Métier, Infra, Perf)
et certifier formellement que le projet est 100% prêt pour la mise en production.
"""

# Variable globale qui va stocker le processus de la sonde pour qu'on puisse l'arreter plus tard pour éviter qu'elle tourne à l'infini en arrière plan
sonde_process = None


TEST_DIR = "infrastructure/tests_infrastructure"


if not os.path.exists("logs"):
    os.makedirs("logs")

# Ici on retrouve tout le pipeline de test que l'on va exécuter avec un ordre précis
# on va de la donnée brute vers l'interface, puis on finit par le stress test.
SCENARIO = [
    {"Etape": "1", "name": "VÉRIFICATION : Fraîcheur des données", "fichier": "test_check.py"},
    {"Etape": "2", "name": "VÉRIFICATION : Structure des données", "fichier": "test_data.py"},
    {"Etape": "3", "name": "VÉRIFICATION : Qualité métier", "fichier": "test_quality.py"},
    {"Etape": "4", "name": "SIMULATION : Parcours Utilisateur", "fichier": "test_functional.py"},
    {"Etape": "5", "name": "TEST INFRASTRUCTURE : Stack Monitoring", "fichier": "test_monitoring_stack.py"},
    {"Etape": "6", "name": "TESTS DE PERFORMANCE : Sondes de monitoring", "fichier": "test_monitoring.py"},
    {"Etape": "7", "name": "TESTS DE PERFORMANCE : Crash Test de Surcharge", "fichier": "test_surcharge.py"}
]



def run_test(test_info):
    """ Exécute un script de test en gérant tous les cas particuliers, il nous permet entre autre de gérer les deux scripts de performance """
    global sonde_process
    script_path = os.path.join(TEST_DIR, test_info["fichier"])
    
    print(f"\n{test_info['Etape']} Lancement de : {test_info['name']} ({test_info['fichier']})...", flush=True)
    
    # on vérifie si le fichier existe avant de le lancer
    if not os.path.exists(script_path):
        print(f"ERREUR CRITIQUE : Le fichier {script_path} est introuvable.", flush=True)
        return False

    # Gestion de la Sonde en Arrière-plan)
    if test_info["fichier"] == "test_monitoring.py":
        print("(Lancement de la sonde en tâche de fond)", flush=True)
        # Popen exécute le script en asynchrone (le programme principal n'attend pas qu'il se termine)
        # L'argument "-u" empêche Python de mettre les prints en mémoire tampon
        sonde_process = subprocess.Popen([sys.executable, "-u", script_path])
        time.sleep(2)
        print(f"{test_info['name']} : LANCÉ EN ARRIÈRE-PLAN\n", flush=True)
        return True 


    # Gestion de L'Attaque qui doit tuer la sonde à la fin
    elif test_info["fichier"] == "test_surcharge.py":
        print("(Lancement des requetes HTTP en surnombre )", flush=True)
        #on attend que l'attaque de surcharge soit complètement terminée
        result = subprocess.run([sys.executable, "-u", script_path])
        
        # Quand l'attaque est finie, on nettoie l'arrière-plan en coupant la sonde
        if sonde_process:
            print("\nFin de la surcharge : Arrêt de la sonde de monitoring.", flush=True)
            sonde_process.terminate() 
            sonde_process.wait()    
            sonde_process = None      
            
        if result.returncode == 0:
            print(f"{test_info['name']} : SUCCÈS\n", flush=True)
            return True
        else:
            print(f"{test_info['name']} : ÉCHEC (Code erreur: {result.returncode})\n", flush=True)
            return False

    # Gestion des autres tests classiques (Synchrones)
    else:
        result = subprocess.run([sys.executable, "-u", script_path])
        if result.returncode == 0:
            print(f"{test_info['name']} : SUCCÈS\n", flush=True)
            return True
        else:
            print(f"{test_info['name']} : ÉCHEC (Code erreur: {result.returncode})\n", flush=True)
            return False

def main():
    start_time = time.time()
    print(f"DÉMARRAGE DU SCÉNARIO DE TEST GLOBAL !")
    
    success_count = 0
    
    # On boucle sur chaque test défini dans le SCENARIO
    for test in SCENARIO:
        time.sleep(1)
        
        # Si un test échoue, on arrête tout immédiatement
        if run_test(test):
            success_count += 1
        else:
            print(f"ARRÊT DU SCÉNARIO (UNE ÉTAPE A ÉCHOUÉ) !")
            sys.exit(1)
            
    end_time = time.time()
    duration = round(end_time - start_time, 2)
    
    print(f"VALIDATION COMPLÈTE ({success_count}/{len(SCENARIO)} tests) en {duration}s !", flush=True)
    print("Tous les tests sont passés et ont été validés, le système est donc prêt pour la production !", flush=True)

if __name__ == "__main__":
    main()