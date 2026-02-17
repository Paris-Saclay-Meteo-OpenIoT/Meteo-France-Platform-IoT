# scheduler.py
import time
import subprocess
from download_data import download_and_extract


while True:
    print("Start training...")
    download_and_extract()
    print("Running forecast...")
    subprocess.run([
        "python3",
        "nwptcn.py",
        "--input_days", "7",
        "--horizon_days", "7"
    ])
    print("Running rain forecast...")
    subprocess.run([
        "python3",
        "nwprain.py",
    ])
    print("Done. Sleep 3 days...")
    time.sleep(3 * 24 * 60 * 60)