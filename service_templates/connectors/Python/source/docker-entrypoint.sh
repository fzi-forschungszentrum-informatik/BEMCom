#!/bin/bash
echo "docker-entrypoint.sh: Starting up"

# Populates the environment variables for the MQTT topics according to the topic convention
# specified in the message format documentation.
echo "docker-entrypoint.sh: Populating environment varables for connector: ${CONNECTOR_NAME}"
export MQTT_TOPIC_LOGS="${CONNECTOR_NAME}/logs"
export MQTT_TOPIC_HEARTBEAT="${CONNECTOR_NAME}/heartbeat"
export MQTT_TOPIC_AVAILABLE_DATAPOINTS="${CONNECTOR_NAME}/available_datapoints"
export MQTT_TOPIC_DATAPOINT_MAP="${CONNECTOR_NAME}/datapoint_map"
export MQTT_TOPIC_RAW_MESSAGE_TO_DB="${CONNECTOR_NAME}/raw_message_to_db"
export MQTT_TOPIC_RAW_MESSAGE_REPROCESS="${CONNECTOR_NAME}/raw_message_reprocess"
export MQTT_TOPIC_DATAPOINT_MESSAGE_WILDCARD="${CONNECTOR_NAME}/messages/#"

python3 /source/connector/main.py &

# Patches SIGTERM and SIGINT to stop the service. This is required
# to trigger graceful shutdown if docker wants to stop the container.
service_pid=$!
trap "kill -TERM $service_pid" SIGTERM
trap "kill -INT $service_pid" INT

# Run until the container is stopped. Give the service maximal 2 seconds to
# clean up and shut down, afterwards we pull the plug hard.
wait
sleep 2
