# download_data.py
import requests
import gzip
import shutil

URL = "https://www.data.gouv.fr/api/1/datasets/r/6da34803-83d6-489a-862c-1b4ab8d0c4d9"

def download_and_extract():
    r = requests.get(URL, stream=True)
    with open("data.csv.gz", "wb") as f:
        f.write(r.content)

    with gzip.open("data.csv.gz", "rb") as f_in:
        with open("H_20_latest-2025-2026.csv", "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


if __name__ == "__main__":
    print("Downloading dataset...")
    download_and_extract()
    print("Download finished.")