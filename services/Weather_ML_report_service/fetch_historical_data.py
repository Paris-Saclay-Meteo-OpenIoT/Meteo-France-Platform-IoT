#!/usr/bin/env python3
"""
Script pour récupérer les données climatologiques HISTORIQUES (1 an par défaut)
depuis l'API Météo-France DPClim pour les 23 stations corses.
Insère directement dans PostgreSQL (weather_data) pour le pipeline ML.

Usage dans le container Docker :
    python fetch_historical_data.py              # 1 an d'historique
    python fetch_historical_data.py --months 6   # 6 mois
    python fetch_historical_data.py --months 3   # 3 mois (rapide)

Utilise le même protocole que api_climatologique_producer :
  1. POST /commande-station/horaire  →  obtenir un command_id
  2. GET  /commande/fichier           →  récupérer le CSV (retry si pending)
"""

import os
import sys
import csv
import io
import time
import logging
import argparse
import asyncio

import httpx
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────
API_BASE_URL = "https://public-api.meteofrance.fr/public/DPClim/v1"
API_TOKEN = os.getenv("API_TOKEN_CLIMA") or os.getenv("API_TOKEN")

POSTGRES_USER = os.getenv("POSTGRES_USER", "weatherapp")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "your_postgres_password_here")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "ter_postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "meteo_db")

DB_URI = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

DELAY_BETWEEN_REQUESTS = 2.5   # secondes – quota API 50 req/min
FETCH_TIMEOUT = 30             # timeout HTTP (historique = gros fichiers)

# ─── 23 stations corses actives sur la carte (corseStations.js) ───────────────
CORSE_STATIONS = [
    {"station_id": "20004002", "nom": "AJACCIO",                "lat": 41.918,    "lon": 8.792667},
    {"station_id": "20040004", "nom": "BOCOGNANO",              "lat": 42.104167, "lon": 9.103333},
    {"station_id": "20047006", "nom": "CALACUCCIA",             "lat": 42.3315,   "lon": 9.0215},
    {"station_id": "20050001", "nom": "CALVI",                  "lat": 42.5295,   "lon": 8.7915},
    {"station_id": "20092001", "nom": "CONCA",                  "lat": 41.717,    "lon": 9.3485},
    {"station_id": "20093002", "nom": "ILE ROUSSE",             "lat": 42.633333, "lon": 8.9225},
    {"station_id": "20096008", "nom": "CORTE",                  "lat": 42.2885,   "lon": 9.193167},
    {"station_id": "20114002", "nom": "FIGARI",                 "lat": 41.505167, "lon": 9.103667},
    {"station_id": "20148001", "nom": "BASTIA",                 "lat": 42.540667, "lon": 9.485167},
    {"station_id": "20154001", "nom": "MARIGNANA",              "lat": 42.188833, "lon": 8.655333},
    {"station_id": "20160001", "nom": "MOCA-CROCE",             "lat": 41.761667, "lon": 9.0165},
    {"station_id": "20185003", "nom": "OLETTA",                 "lat": 42.632333, "lon": 9.3205},
    {"station_id": "20223001", "nom": "PIETRALBA",              "lat": 42.541,    "lon": 9.172},
    {"station_id": "20232002", "nom": "PILA-CANALE",            "lat": 41.8145,   "lon": 8.903667},
    {"station_id": "20254006", "nom": "QUENZA",                 "lat": 41.777667, "lon": 9.142833},
    {"station_id": "20255003", "nom": "QUERCITELLO",            "lat": 42.426833, "lon": 9.332333},
    {"station_id": "20258001", "nom": "RENNO",                  "lat": 42.190167, "lon": 8.807167},
    {"station_id": "20268001", "nom": "SAMPOLO",                "lat": 41.943,    "lon": 9.123},
    {"station_id": "20270001", "nom": "SARI D'ORCINO",          "lat": 42.0785,   "lon": 8.802333},
    {"station_id": "20272004", "nom": "SARTENE",                "lat": 41.652333, "lon": 8.979333},
    {"station_id": "20303002", "nom": "ALISTRO",                "lat": 42.259667, "lon": 9.5415},
    {"station_id": "20314006", "nom": "SANTO PIETRO DI TENDA",  "lat": 42.635833, "lon": 9.200667},
    {"station_id": "20342001", "nom": "SOLENZARA",              "lat": 41.921833, "lon": 9.400833},
]


# ══════════════════════════════════════════════════════════════════════════════
# API helpers  (même protocole que api_climatologique_producer/producer.py)
# ══════════════════════════════════════════════════════════════════════════════

def csv_to_dicts(csv_text, delimiter=";"):
    """Parse le CSV retourné par l'API DPClim en liste de dicts."""
    f = io.StringIO(csv_text)
    reader = csv.reader(f, delimiter=delimiter)
    headers = next(reader, None)
    if not headers:
        return []

    def _cell(c):
        c = c.strip()
        if c == "":
            return None
        c = c.replace(",", ".")
        try:
            return float(c)
        except ValueError:
            return c

    return [{h: _cell(c) for h, c in zip(headers, row)} for row in reader]


async def create_command(station_id: str, start_date: str, end_date: str):
    """POST commande-station/horaire → retourne command_id ou None."""
    url = f"{API_BASE_URL}/commande-station/horaire"
    headers = {"accept": "application/json", "apikey": API_TOKEN}
    params = {
        "id-station": station_id,
        "date-deb-periode": start_date,
        "date-fin-periode": end_date,
    }
    async with httpx.AsyncClient(timeout=FETCH_TIMEOUT) as client:
        for attempt in range(1, 4):
            try:
                resp = await client.get(url, headers=headers, params=params)
                await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
                if resp.status_code == 202:
                    try:
                        return resp.json()["elaboreProduitAvecDemandeResponse"]["return"]
                    except KeyError:
                        logger.error(f"[{station_id}] 202 sans ID: {resp.text[:200]}")
                        return None
                elif resp.status_code == 429:
                    logger.warning(f"[{station_id}] 429 quota — attente 90s (try {attempt})")
                    await asyncio.sleep(90)
                else:
                    logger.error(f"[{station_id}] Commande err {resp.status_code}: {resp.text[:200]}")
                    return None
            except httpx.RequestError as e:
                logger.error(f"[{station_id}] Réseau: {e}")
                await asyncio.sleep(5 * attempt)
    return None


async def fetch_csv(command_id: str):
    """GET commande/fichier → retourne liste de dicts ou None."""
    url = f"{API_BASE_URL}/commande/fichier"
    headers = {"accept": "*/*", "apikey": API_TOKEN}
    params = {"id-cmde": command_id}
    async with httpx.AsyncClient(timeout=FETCH_TIMEOUT) as client:
        for attempt in range(1, 20):  # plus de tentatives pour historique long
            try:
                resp = await client.get(url, headers=headers, params=params)
                await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
                if resp.status_code == 201:
                    return csv_to_dicts(resp.text)
                elif resp.status_code in (204, 404):
                    logger.info(f"  [cmd {command_id}] pending ({attempt}/19), attente 30s")
                    await asyncio.sleep(30)
                elif resp.status_code == 429:
                    logger.warning(f"  [cmd {command_id}] 429 quota — attente 90s")
                    await asyncio.sleep(90)
                else:
                    logger.error(f"  [cmd {command_id}] Erreur {resp.status_code}")
                    return None
            except httpx.RequestError as e:
                logger.error(f"  [cmd {command_id}] Réseau: {e}")
                await asyncio.sleep(5 * attempt)
    logger.error(f"  [cmd {command_id}] Timeout toutes tentatives")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Transformation + PostgreSQL
# ══════════════════════════════════════════════════════════════════════════════

def _safe_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def transform_rows(rows, station):
    """Convertit les lignes brutes DPClim → format weather_data."""
    records = []
    for row in rows:
        try:
            date_raw = row.get("DATE") or row.get("date")
            if date_raw is None:
                continue
            ds = str(date_raw).replace(".0", "")
            if len(ds) == 10 and ds.isdigit():
                dt = datetime.strptime(ds, "%Y%m%d%H")
            elif "T" in ds:
                dt = datetime.fromisoformat(ds.replace("Z", ""))
            else:
                dt = pd.to_datetime(ds)

            t = _safe_float(row.get("T") or row.get("t"))
            u = _safe_float(row.get("U") or row.get("u"))
            ff = _safe_float(row.get("FF") or row.get("ff"))
            rr1 = _safe_float(row.get("RR1") or row.get("rr1"))

            if t is None and u is None and ff is None and rr1 is None:
                continue

            records.append({
                "station_id": station["station_id"],
                "nom_usuel": station["nom"],
                "lat": station["lat"],
                "lon": station["lon"],
                "date": dt,
                "t": t,
                "u": u,
                "ff": ff,
                "rr1": rr1 if rr1 is not None else 0.0,
            })
        except Exception:
            continue
    return records


def ensure_table(engine):
    """Crée weather_data si absente."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS weather_data (
                id SERIAL,
                nom_usuel VARCHAR(255),
                station_id VARCHAR(255),
                date TIMESTAMP,
                t FLOAT, u FLOAT, ff FLOAT, rr1 FLOAT,
                lat FLOAT, lon FLOAT,
                dd INT DEFAULT NULL, n INT DEFAULT NULL, vis INT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(station_id, date)
            );
        """))
        conn.commit()


def insert_records(engine, records):
    """Upsert dans weather_data."""
    if not records:
        return 0
    with engine.connect() as conn:
        for r in records:
            conn.execute(text("""
                INSERT INTO weather_data (station_id, nom_usuel, lat, lon, date, t, u, ff, rr1)
                VALUES (:station_id, :nom_usuel, :lat, :lon, :date, :t, :u, :ff, :rr1)
                ON CONFLICT (station_id, date) DO UPDATE SET
                    t = COALESCE(EXCLUDED.t, weather_data.t),
                    u = COALESCE(EXCLUDED.u, weather_data.u),
                    ff = COALESCE(EXCLUDED.ff, weather_data.ff),
                    rr1 = COALESCE(EXCLUDED.rr1, weather_data.rr1),
                    nom_usuel = EXCLUDED.nom_usuel,
                    lat = EXCLUDED.lat, lon = EXCLUDED.lon
            """), r)
        conn.commit()
    return len(records)


# ══════════════════════════════════════════════════════════════════════════════
# Orchestration par mois
# ══════════════════════════════════════════════════════════════════════════════

def month_chunks(start_dt, end_dt):
    """Découpe la plage en morceaux mensuels (l'API DPClim est plus stable)."""
    chunks = []
    cur = start_dt.replace(day=1)
    while cur < end_dt:
        nxt_month = (cur.month % 12) + 1
        nxt_year = cur.year + (1 if nxt_month == 1 else 0)
        nxt = cur.replace(year=nxt_year, month=nxt_month, day=1)
        chunk_end = min(nxt - timedelta(seconds=1), end_dt)
        chunks.append((cur, chunk_end))
        cur = nxt
    return chunks


async def fetch_station_history(station, start_dt, end_dt, engine):
    """Récupère l'historique complet d'une station, mois par mois."""
    sid = station["station_id"]
    nom = station["nom"]
    total = 0

    chunks = month_chunks(start_dt, end_dt)
    for ci, (cs, ce) in enumerate(chunks, 1):
        s_str = cs.strftime("%Y-%m-%dT00:00:00Z")
        e_str = ce.strftime("%Y-%m-%dT23:59:59Z")
        logger.info(f"   📅 [{sid}] chunk {ci}/{len(chunks)}: {cs.strftime('%Y-%m')} → {ce.strftime('%Y-%m')}")

        cmd_id = await create_command(sid, s_str, e_str)
        if not cmd_id:
            logger.warning(f"   ⚠️  [{sid}] commande échouée pour {cs.strftime('%Y-%m')}")
            continue

        rows = await fetch_csv(cmd_id)
        if not rows:
            logger.warning(f"   ⚠️  [{sid}] CSV vide pour {cs.strftime('%Y-%m')}")
            continue

        records = transform_rows(rows, station)
        if records:
            n = insert_records(engine, records)
            total += n
            logger.info(f"   💾 [{sid}] {n} lignes insérées ({cs.strftime('%Y-%m')})")

    logger.info(f"   ✅ [{sid}] {nom}: {total} enregistrements au total")
    return total


# ══════════════════════════════════════════════════════════════════════════════
# Point d'entrée
# ══════════════════════════════════════════════════════════════════════════════

async def main_async(months=12):
    if not API_TOKEN:
        logger.error("❌ API_TOKEN_CLIMA non défini ! "
                      "Ajoutez-le dans docker-compose.yml env weather_ml_service")
        sys.exit(1)

    logger.info("=" * 80)
    logger.info("🌍 RÉCUPÉRATION DES DONNÉES HISTORIQUES MÉTÉO-FRANCE (DPClim)")
    logger.info(f"   📅 Période : {months} mois")
    logger.info(f"   🏔️  Stations : {len(CORSE_STATIONS)}")
    logger.info("=" * 80)

    end_dt = datetime.utcnow() - timedelta(days=1)
    start_dt = end_dt - timedelta(days=months * 30)

    logger.info(f"   📅 Plage : {start_dt.date()} → {end_dt.date()}")

    engine = create_engine(DB_URI)
    ensure_table(engine)

    # Vérifier la date la plus récente par station
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT station_id, COUNT(*), MAX(date) FROM weather_data GROUP BY station_id"
        ))
        existing_info = {r[0]: {"count": r[1], "max_date": r[2]} for r in result.fetchall()}

    total_inserted = 0
    failed = []
    skipped = 0

    for i, station in enumerate(CORSE_STATIONS, 1):
        sid = station["station_id"]
        info = existing_info.get(sid, {"count": 0, "max_date": None})
        existing = info["count"]
        max_date = info["max_date"]

        # Skip uniquement si les données sont déjà à jour (< 2 jours de retard)
        if max_date and (end_dt - max_date).days < 2 and existing >= 100:
            logger.info(f"[{i}/{len(CORSE_STATIONS)}] {station['nom']} ({sid}) — ⏭️  {existing} lignes, à jour jusqu'au {max_date.strftime('%Y-%m-%d')}")
            skipped += 1
            continue

        # Ajuster start_dt pour ne récupérer que les données manquantes
        station_start = start_dt
        if max_date and max_date > start_dt:
            station_start = max_date - timedelta(hours=1)
            logger.info(f"\n{'─' * 60}")
            logger.info(f"[{i}/{len(CORSE_STATIONS)}] {station['nom']} ({sid}) — {existing} lignes, dernière: {max_date.strftime('%Y-%m-%d %H:%M')}")
            logger.info(f"   🔄 Récupération depuis {station_start.strftime('%Y-%m-%d')}")
            logger.info(f"{'─' * 60}")
        else:
            logger.info(f"\n{'─' * 60}")
            logger.info(f"[{i}/{len(CORSE_STATIONS)}] {station['nom']} ({sid}) — {existing} lignes existantes")
            logger.info(f"{'─' * 60}")

        try:
            n = await fetch_station_history(station, station_start, end_dt, engine)
            if n == 0:
                failed.append(station["nom"])
            total_inserted += n
        except Exception as e:
            failed.append(station["nom"])
            logger.error(f"   ❌ {station['nom']}: {e}")

        if i < len(CORSE_STATIONS):
            await asyncio.sleep(3)

    logger.info("\n" + "=" * 80)
    logger.info("📊 RÉSUMÉ")
    logger.info("=" * 80)
    logger.info(f"   ✅ Total insérés : {total_inserted}")
    logger.info(f"   📡 Stations OK   : {len(CORSE_STATIONS) - len(failed) - skipped}/{len(CORSE_STATIONS)}")
    logger.info(f"   ⏭️  Stations skip : {skipped} (déjà à jour)")
    if failed:
        logger.warning(f"   ⚠️  Échecs : {', '.join(failed)}")
    logger.info("=" * 80)
    engine.dispose()
    return total_inserted


def main():
    parser = argparse.ArgumentParser(
        description="Récupère les données historiques Météo-France pour la Corse"
    )
    parser.add_argument("--months", type=int, default=12,
                        help="Nombre de mois d'historique (défaut: 12)")
    args = parser.parse_args()
    asyncio.run(main_async(months=args.months))


if __name__ == "__main__":
    main()
