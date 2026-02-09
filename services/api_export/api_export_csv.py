from fastapi import FastAPI, Response
import csv
import io
import logging
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()


# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Postgres Configuration
PG_USER = os.getenv("POSTGRES_USER", "my_user")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "my_password")
PG_DB = os.getenv("POSTGRES_DB", "my_database")
PG_HOST = os.getenv("POSTGRES_HOST", "ter_postgres") 
PG_PORT = os.getenv("POSTGRES_PORT", "5432")

# Exposed endpoint : http://localhost:8000/health
@app.get("/health")
def health_check():
    return {"status": "ok"}

def get_db_connection():
    try:
        conn = psycopg2.connect(
            user=PG_USER,
            password=PG_PASS,
            dbname=PG_DB,
            host=PG_HOST,
            port=PG_PORT
        )
        return conn
    except Exception as e:
        logger.error(f"Erreur de connexion DB: {e}")
        return None

# Mapping dict: CSV Header -> Postgres Column Name
mapping = {
    "NUM_POSTE": "station_id",   
    "AAAAMMJJHH": "formatted_date" 
}

# Static values 
defaults = {
    "NOM_USUEL": "AJACCIO",
    "LAT": "41.918",
    "LON": "8.792667",
    "ALTI": "5"
}

# The Header Line (Météo France Standard)
header_line = (
    "NUM_POSTE;NOM_USUEL;LAT;LON;ALTI;AAAAMMJJHH;RR1;QRR1;DRR1;QDRR1;"
    "FF;QFF;DD;QDD;FXY;QFXY;DXY;QDXY;HXY;QHXY;FXI;QFXI;DXI;QDXI;"
    "HXI;QHXI;FF2;QFF2;DD2;QDD2;FXI2;QFXI2;DXI2;QDXI2;HXI2;QHXI2;"
    "FXI3S;QFXI3S;DXI3S;QDXI3S;HFXI3S;QHFXI3S;T;QT;TD;QTD;TN;QTN;"
    "HTN;QHTN;TX;QTX;HTX;QHTX;DG;QDG;T10;QT10;T20;QT20;T50;QT50;"
    "T100;QT100;TNSOL;QTNSOL;TN50;QTN50;TCHAUSSEE;QTCHAUSSEE;DHUMEC;"
    "QDHUMEC;U;QU;UN;QUN;HUN;QHUN;UX;QUX;HUX;QHUX;DHUMI40;QDHUMI40;"
    "DHUMI80;QDHUMI80;TSV;QTSV;PMER;QPMER;PSTAT;QPSTAT;PMERMIN;QPMERMIN;"
    "GEOP;QGEOP;N;QN;NBAS;QNBAS;CL;QCL;CM;QCM;CH;QCH;N1;QN1;C1;QC1;"
    "B1;QB1;N2;QN2;C2;QC2;B2;QB2;N3;QN3;C3;QC3;B3;QB3;N4;QN4;C4;"
    "QC4;B4;QB4;VV;QVV;DVV200;QDVV200;WW;QWW;W1;QW1;W2;QW2;SOL;QSOL;"
    "SOLNG;QSOLNG;TMER;QTMER;VVMER;QVVMER;ETATMER;QETATMER;DIRHOULE;"
    "QDIRHOULE;HVAGUE;QHVAGUE;PVAGUE;QPVAGUE;HNEIGEF;QHNEIGEF;NEIGETOT;"
    "QNEIGETOT;TSNEIGE;QTSNEIGE;TUBENEIGE;QTUBENEIGE;HNEIGEFI3;QHNEIGEFI3;"
    "HNEIGEFI1;QHNEIGEFI1;ESNEIGE;QESNEIGE;CHARGENEIGE;QCHARGENEIGE;"
    "GLO;QGLO;GLO2;QGLO2;DIR;QDIR;DIR2;QDIR2;DIF;QDIF;DIF2;QDIF2;"
    "UV;QUV;UV2;QUV2;UV_INDICE;QUV_INDICE;INFRAR;QINFRAR;INFRAR2;QINFRAR2;"
    "INS;QINS;INS2;QINS2;TLAGON;QTLAGON;TVEGETAUX;QTVEGETAUX;ECOULEMENT;QECOULEMENT"
)
headers = header_line.split(";")

# Exposed endpoint : http://localhost:8000/export-csv
@app.get("/export-csv")
def export_csv():
    conn = get_db_connection()
    if not conn:
        return Response(content="Erreur de connexion à la base de données", status_code=500)

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # SQL Query:
        query = """
            SELECT 
                TO_CHAR(reference_time, 'YYYYMMDDHH24') as formatted_date,
                * FROM weather_measurements
            ORDER BY reference_time DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        logger.info("Lignes récupérées depuis Postgres: %d", len(rows))
        
        if not rows:
            return Response(content="Aucune donnée trouvée", media_type="text/plain")

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers, delimiter=';')
        writer.writeheader()

        for db_row in rows:
            csv_row = {}
            for h in headers:
                # 1. Check Specific Mapping (NUM_POSTE, AAAAMMJJHH)
                if h in mapping:
                    val = db_row.get(mapping[h])
                    csv_row[h] = str(val) if val is not None else ""
                
                # 2. Check Direct Mapping (e.g., CSV 'RR1' -> DB 'rr1')
                elif h.lower() in db_row:
                    val = db_row.get(h.lower())
                    csv_row[h] = str(val) if val is not None else ""
                
                # 3. Check Defaults (LAT, LON, ALTI...)
                elif h in defaults:
                    csv_row[h] = defaults[h]
                
                # 4. Empty otherwise
                else:
                    csv_row[h] = ""
            
            writer.writerow(csv_row)

        csv_content = output.getvalue()
        output.close()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=weatherData_AI.csv"}
        )

    except Exception as e:
        logger.error(f"Erreur lors de l'export: {e}")
        return Response(content=f"Erreur interne: {str(e)}", status_code=500)
    
    finally:
        if conn:
            conn.close()