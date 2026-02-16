# scheduler.py
import time
import subprocess
from download_data import download_and_extract
#from train import train


while True:
    print("Start training...")
    download_and_extract()
    #print("Training TCN...")
    #train()
    print("Running forecast temperature...")
    subprocess.run([
        "python3",
        "nwptcn.py",
        "--input_days", "7",
        "--horizon_days", "7"
    ])
    print("Done. Sleep 3 days...")
    time.sleep(3 * 24 * 60 * 60)