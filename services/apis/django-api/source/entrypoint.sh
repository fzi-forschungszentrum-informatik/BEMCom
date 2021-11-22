#!/bin/bash
set -e
set -u

echo "Entering entrypoint.sh"

# Ensure the DB layout matches the current state of the application
printf "\n\nCreating and applying migrations."
python3 /source/api/manage.py makemigrations
python3 /source/api/manage.py migrate

# Run prod deploy checks if not in devl.
if [ "${DJANGO_DEBUG:-False}" != "TRUE" ]
then
    printf "\n\n"
    echo "Running Djangos production deploy checks"
    python3 /source/api/manage.py check --deploy
    printf "\nDjango production tests done\n\n"
fi

# Create the admin account from environment variables.
if [ ! -z "${DJANGO_SUPERUSER_PASSWORD}" ] && [ ! -z "${DJANGO_SUPERUSER_USERNAME}" ] && [ ! -z "${DJANGO_SUPERUSER_EMAIL}" ]
then
  printf "\n\n"
  echo "Attempting to create admin account for user $DJANGO_SUPERUSER_USERNAME"
  # The printf should produce no output but catches errors.
  python3 /source/api/manage.py createsuperuser --no-input || printf ""
fi

# Start MqttToDb in background and patch sigtern and SIGINT signals,
# to trigger graceful shutdown of the component on container exit.
python3 /source/api/manage.py mqtttodb &
service_pid=$!
trap "kill -TERM $service_pid" SIGTERM
trap "kill -INT $service_pid" INT

# Start up the server, use the internal devl server in debug mode.
# Both serve plain http on port 8080 within the container.
if  [[ "${DJANGO_DEBUG:-FALSE}" == "TRUE" ]]
then
    # --noreload prevents duplicate entries in DB.
    printf "\n\nStarting up Django development server.\n\n\n"
    python3 /source/api/manage.py runserver --noreload 0.0.0.0:8080 &
else
    printf "\n\nCollecting static files."
    python3 /source/api/manage.py collectstatic --no-input
    cd /source/api && \
    printf "\n\nStarting up Gunicorn/UVicorn production server.\n\n\n"
    gunicorn api_main.asgi:application --workers ${N_WORKER_PROCESSES:-4} --worker-class uvicorn.workers.UvicornWorker -b 0.0.0.0:8080 &
fi

# Also patch SIGTERM and SIGINT to the django application.
service_pid=$!
trap "kill -TERM $service_pid" SIGTERM
trap "kill -INT $service_pid" INT

# Run until the container is stopped. Give the service maximal 2 seconds to
# clean up and shut down, afterwards we pull the plug hard.
wait
sleep 2
