#!/bin/sh
set -e

echo "Waiting for Kafka to be ready..."
until kafka-topics.sh --list --zookeeper ter_zookeeper:2181; do
  echo "Kafka is not ready yet, retrying in 5 seconds..."
  sleep 5
done

echo "Creating topics..."

# topic API observation
kafka-topics.sh --create --if-not-exists --topic weather-real-time --zookeeper ter_zookeeper:2181 --partitions 1 --replication-factor 1
kafka-configs.sh --zookeeper ter_zookeeper:2181 --entity-type topics --entity-name weather-real-time \
  --alter --add-config retention.ms=7200000

# topic API climatologiques
kafka-topics.sh --create --if-not-exists --topic weather-verified --zookeeper ter_zookeeper:2181 --partitions 1 --replication-factor 1
kafka-configs.sh --zookeeper ter_zookeeper:2181 --entity-type topics --entity-name weather-verified \
  --alter --add-config retention.ms=604800000

# topic API vilgilance
kafka-topics.sh --create --if-not-exists --topic weather-alerts --zookeeper ter_zookeeper:2181 --partitions 1 --replication-factor 1
kafka-configs.sh --zookeeper ter_zookeeper:2181 --entity-type topics --entity-name weather-alerts \
  --alter --add-config retention.ms=86400000

# Ceation of the topic for the lock
kafka-topics.sh --create --if-not-exists --topic climatologique-status --zookeeper ter_zookeeper:2181 --partitions 1 --replication-factor 1

echo "Topics successfully created."

# Publish a message to the lock topic to indicate that the lock is free
# we consider that the absence of climatological activity means that the lock is "free"
echo 'None:{"status": "free", "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"}' | \
  kafka-console-producer.sh --broker-list ter_kafka:9092 --topic climatologique-status --property "parse.key=true" --property "key.separator=:"

echo "Message de verrouillage initial envoyé sur 'climatologique-status'."

touch /topics_initialized
