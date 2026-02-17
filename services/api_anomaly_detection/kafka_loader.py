"""
Kafka data loader for anomaly detection.

Reads all available messages from the weather-verified topic and returns
a flat DataFrame ready to be consumed by CompleteAnomalyDetector.
"""

import json
import logging
import pandas as pd
from kafka import KafkaConsumer

logger = logging.getLogger(__name__)


def load_from_kafka(
    kafka_broker: str,
    topic: str = "weather-verified",
    timeout_ms: int = 10000,
) -> pd.DataFrame:
    """
    Consume all currently available messages from the Kafka topic and return
    a flat DataFrame.

    Uses auto_offset_reset='earliest' and group_id=None so every call reads
    the full retention window (7 days) independently, without committing
    offsets or interfering with other consumer groups.

    Parameters
    ----------
    kafka_broker : str
        Kafka bootstrap server address, e.g. "ter_kafka:9092".
    topic : str
        Kafka topic name.
    timeout_ms : int
        How long (ms) to wait for new messages before stopping. 10 seconds
        is enough because we want all buffered messages, not a live stream.

    Returns
    -------
    pd.DataFrame
        Flat DataFrame where each row is one hourly observation, with the
        same columns as weather_data.parquet (NUM_POSTE, LAT, LON, ALTI,
        AAAAMMJJHH, T, TN, TX, RR1, FF, FXI, TD, U, QT, ...).

    Raises
    ------
    ValueError
        If no messages were found in the topic.
    """
    logger.info("Connecting to Kafka at %s, topic=%s", kafka_broker, topic)

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=kafka_broker,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        group_id=None,          # ephemeral — always reads from earliest
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        consumer_timeout_ms=timeout_ms,
    )

    all_rows = []
    message_count = 0

    for message in consumer:
        data = message.value
        rows = data.get("rows", [])
        all_rows.extend(rows)
        message_count += 1

    consumer.close()

    logger.info("Consumed %d messages → %d rows total", message_count, len(all_rows))

    if not all_rows:
        raise ValueError(
            f"No data received from Kafka topic '{topic}'. "
            "Make sure the climatologique producer has run at least once."
        )

    return pd.DataFrame(all_rows)
