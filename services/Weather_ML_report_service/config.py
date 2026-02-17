import os

# -- Added correct env variables
user = os.getenv("DB_USER", "my_user")
password = os.getenv("DB_PASSWORD", "my_password")
host = os.getenv("DB_HOST", "postgres")
port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME", "my_database")

DB_URI = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

SENDER_EMAIL = "meteofranceparissaclay@gmail.com"
SENDER_PASSWORD = "ibjw rsyg fpje meqw"

DATASET_ID = "6569b4473bedf2e7abad3b72"
DEPT_CODE = "20"