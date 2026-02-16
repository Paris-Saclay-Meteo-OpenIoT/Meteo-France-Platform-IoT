import requests
import sys

"""
C'est un test d'intégrité qui va nous permettre de tester la perméabilité et la fiabilité de Prometheus et Grafana
L'objectif ici est de vérifier et donc valider que le monitoring du projet (grafana & prometheus) est bien en place et utilise les routes standards
établit par le développeur backend.
On va donc avoir un réel retour pour savoir si Prometheus communique réellement avec l'API et si aussi Grafana communique bien avec la BBD en place
"""


URL_PROMETHEUS = "http://localhost:9090"
URL_GRAFANA = "http://localhost:3000"


#fonction classique qui mets en place un code couleur pour les logs de tests.
def log(msg, status="INFO"):
    colors = {"INFO": "\033[94m", "SUCCESS": "\033[92m", "ERROR": "\033[91m", "RESET": "\033[0m"}
    print(f"{colors.get(status, '')}[{status}] {msg}{colors['RESET']}")

print("LANCEMENT DU DIAGNOSTIC DE MONITORING")
print("=" * 10)

failed = False

# Test de Prometheus qui représente ici le cerveau celui qui va exécuter des requêtes PromQL
try:
    # On vérifie la santé global de prometheus
    r = requests.get(f"{URL_PROMETHEUS}/-/healthy", timeout=2)
    
    if r.status_code == 200:
        log("Prometheus est en ligne !", "SUCCESS")
        
        #Ici on va commencer par interroger la liste des cibles actives que l'on retrouve
        try:
            r2 = requests.get(f"{URL_PROMETHEUS}/api/v1/targets", timeout=2)
            data = r2.json()
            active_targets = data.get('data', {}).get('activeTargets', [])

            # On cherche si on trouve des cibles justement
            found_targets = [t['labels']['job'] for t in active_targets if t['health'] == 'up']
            
            if len(found_targets) > 0:
                log(f"Prometheus surveille activement : {found_targets}", "SUCCESS")
                log("Le lien entre Prometheus et le projet est donc valide !", "SUCCESS")
            else:
                log("Prometheus fonctionne, mais ne voit AUCUNE cible", "WARN")
                
        except Exception as e:
            log(f"Erreur lors de l'analyse des cibles : {e}", "WARN")

    else:
        log(f"Prometheus répond une erreur {r.status_code}", "ERROR")
        failed = True

except requests.exceptions.ConnectionError:
    log("Impossible de se connecter à localhost:9090", "ERROR")
    failed = True

# Test ici de Grafana qui va se connecter à la BDD interne pour charger des dashboards.
try:
    # # On vérifie la santé global de grafana
    r = requests.get(f"{URL_GRAFANA}/api/health", timeout=2)
    if r.status_code == 200:
        log("Grafana est en ligne !", "SUCCESS")
        db_state = r.json().get('database', 'unknown')
        log(f"Base de données Grafana : {db_state}", "SUCCESS")
    else:
        log(f"Grafana répond une erreur {r.status_code}", "ERROR")
        failed = True
except requests.exceptions.ConnectionError:
    log("Impossible de se connecter à localhost:3000", "ERROR")
    failed = True

# Bilan global du test fonctionnel
print("-" * 10)
if failed:
    log("ÉCHEC : Un composant du monitoring est hors service !!", "ERROR")
    sys.exit(1)
else:
    log("SUCCÈS : La stack de monitoring est totalement Opérationnelle.", "SUCCESS")
    sys.exit(0)