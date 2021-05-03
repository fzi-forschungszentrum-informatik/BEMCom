#!/bin/bash
echo "docker-entrypoint.sh: Starting up"

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
