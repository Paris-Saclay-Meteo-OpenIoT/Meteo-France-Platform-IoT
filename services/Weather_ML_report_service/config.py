import os

# ✅ Utilise les variables d'environnement pour la flexibilité
POSTGRES_USER = os.getenv("POSTGRES_USER", "weatherapp")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "your_postgres_password_here")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "ter_postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "meteo_db")  # ✅ Bonne base de données

DB_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

SENDER_EMAIL = "meteofranceparissaclay@gmail.com"
SENDER_PASSWORD = "ibjw rsyg fpje meqw"

DATASET_ID = "6569b4473bedf2e7abad3b72"
DEPT_CODE = "20"