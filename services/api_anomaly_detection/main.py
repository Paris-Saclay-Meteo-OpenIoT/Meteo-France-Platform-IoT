"""
Anomaly Detection Service — Entry Point
========================================
Loads weather data from Kafka (weather-verified topic) and runs the
3-level anomaly detection pipeline on a schedule.
"""

import logging
import os
from apscheduler.schedulers.blocking import BlockingScheduler

from complete_anomaly_detector import CompleteAnomalyDetector
from config_3level import get_detector_config
from kafka_loader import load_from_kafka
from manual_detection import export_for_frontend

# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "ter_kafka:9092")
DETECTION_INTERVAL_HOURS = int(os.getenv("DETECTION_INTERVAL_HOURS", "24"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
import pathlib
pathlib.Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/anomaly_detection.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Detection cycle
# ---------------------------------------------------------------------------
def run_detection():
    logger.info("=== Starting anomaly detection cycle ===")

    try:
        df = load_from_kafka(KAFKA_BROKER)
    except ValueError as e:
        logger.error("Data loading failed: %s", e)
        return

    config = get_detector_config(sensitivity="medium")
    detector = CompleteAnomalyDetector(**config)

    # Inject the Kafka DataFrame so load_and_preprocess_data skips the
    # parquet read (see the patched check in complete_anomaly_detector.py).
    detector.df = df

    df_full, df_anomalies = detector.run_full_pipeline()

    logger.info("Total observations: %d", len(df_full))
    logger.info("Total anomalies:    %d (%.2f%%)", len(df_anomalies), 100 * len(df_anomalies) / len(df_full))

    export_for_frontend(df_full, df_anomalies, detector)
    logger.info("Frontend output written to frontend_output/")
    logger.info("=== Detection cycle complete ===")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Run once immediately on startup, then on schedule.
    run_detection()

    scheduler = BlockingScheduler()
    scheduler.add_job(run_detection, "interval", hours=DETECTION_INTERVAL_HOURS)
    logger.info("Scheduled to run every %d hour(s).", DETECTION_INTERVAL_HOURS)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
