#train.py
import subprocess
import sys

def train():
    print("Launching TCN training...")

    result = subprocess.run(
        [
            "python3",
            "train_tcn_temperature.py",
            "--input_days", "14"
        ],
        capture_output=True,
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        print("Training FAILED")
        print(result.stderr)
        sys.exit(1)   # Exit with error code to indicate failure
    else:
        print("Training SUCCESS")