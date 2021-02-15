#!/bin/
set -e
# Create a fallback SECRET_KEY for django, that can be used if the user has 
# not specified SECRET_KEY explicitly. Exporting the env variable here will
# work for starting up the django app, but not for any other shell that requires
# django settings to be set up correctly, like e.g. creating a super user from 
# terminal. Hence we store the secret key in an env file where it is picked
# up by settings.py.
if [ -z "$DJANGO_SECRET_KEY" ]
then
    echo "DJANGO_SECRET_KEY=$(< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c64)" > /bemcom/.env
fi

# Check that the Hostname is not empty in production. It's absolutely required.
printf "Checking Hostname: $HOSTNAME\n\n"
if [ $MODE != "DEVL" ] && [ -z "$HOSTNAME" ]
then
    echo "Error: Environment variable HOSTNAME is not set."
    exit 1
fi

# Add Hostname to Allowed hosts to make the server accesible.
echo ALLOWED_HOSTS="['$HOSTNAME']" >> /bemcom/.env

# Ensure the DB layout matches the current state of the application
python3 /bemcom/code/manage.py makemigrations
python3 /bemcom/code/manage.py migrate

# Run prod deploy checks if not in devl.
if [ $MODE != "DEVL" ]
then
    printf "\n"
    echo "Running Djangos production deploy checks"
    python3 /bemcom/code/manage.py check --deploy
    printf "\nDjango production tests done\n\n"
fi

# Check if SSL certificates have been provided by the user. If yes use there.
# If not create self signed certificates.
# Use a directory in tmp as the user might have no write access for the /bemcom folder.
echo "Checking the certificate situation."
mkdir -p /tmp/cert
chmod 700 /tmp/cert
cd /tmp/cert
if [ -z "$SSL_CERT_PEM" ] || [ -z "$SSL_KEY_PEM" ]
then
    # As proposed by:
    # https://stackoverflow.com/questions/10175812/how-to-create-a-self-signed-certificate-with-openssl
    echo "Environment variables SSL_CERT_PEM or SSL_KEY_PEM empty."
    echo "Generating self signed certificate."
    openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=$HOSTNAME"
else
    # write the users cert and key to file if both have been provided. 
    echo "The user provided cert.pem and key.pem"
    printf "\ncert.pem:\n$SSL_CERT_PEM\n\n"
    echo "$SSL_CERT_PEM" > cert.pem
    echo "$SSL_KEY_PEM" > key.pem
fi



# Run tests for the log to see if we expect the API to work properly
cd /bemcom
pytest /bemcom/code/

# Start up the server, use the internal devl server in devl mode.
# Both should bind to port 8000 within the container and start the server.
if [ $MODE == "DEVL" ]
then
    # --noreload prevents duplicate entries in DB.
    python3 /bemcom/code/manage.py runserver --noreload 0.0.0.0:8000
else
    python3 /bemcom/code/manage.py collectstatic
    cd /bemcom/code && \
    daphne -e ssl:8000:privateKey=/tmp/cert/key.pem:certKey=/tmp/cert/cert.pem \
           -b 0.0.0.0 \
           -p 8080 general_configuration.asgi:application
fi
