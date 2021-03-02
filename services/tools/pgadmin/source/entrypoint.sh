#!/bin/bash
set -e

echo "Entering entrypoint.sh"

# Check if SSL certificates have been provided by the user. If yes use there.
# If not create self signed certificates.
printf "\n\n"
echo "Checking the certificate situation."
if [ -z "$SSL_CERT_PEM" ] || [ -z "$SSL_KEY_PEM" ]
then
    # As proposed by:
    # https://stackoverflow.com/questions/10175812/how-to-create-a-self-signed-certificate-with-openssl
    echo "Environment variables SSL_CERT_PEM or SSL_KEY_PEM empty."
    echo "Generating self signed certificate."
    openssl req -x509 -newkey rsa:4096 -keyout /certs/server.key -out /certs/server.cert -days 365 -nodes -subj "/CN=$HOSTNAME"
else
    # write the users cert and key to file if both have been provided.
    echo "The user provided cert.pem and key.pem"
    printf "\ncert.pem:\n$SSL_CERT_PEM\n\n"
    echo "$SSL_CERT_PEM" > /certs/server.key
    echo "$SSL_KEY_PEM" > /certs/server.cert
fi

# Starting the pgadmin entrypoint.
sh /entrypoint.sh
