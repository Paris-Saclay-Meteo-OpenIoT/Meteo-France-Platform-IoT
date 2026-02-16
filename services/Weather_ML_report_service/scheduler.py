import schedule
import time
from main import run_pipeline

schedule.every().day.at("00:00").do(run_pipeline)

print("Scheduler Météo AI Démarré...")

while True:
    schedule.run_pending()
    time.sleep(60)