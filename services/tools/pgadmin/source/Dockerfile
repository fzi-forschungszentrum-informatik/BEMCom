FROM dpage/pgadmin4:5


# Create the required folder structure and give any user read/write
# access as the container may be run with arbitrary user_id to prevent
# file permission errors on the host.
# Also Add folder where the SQLite DB should be stored.
# This must be a folder due to the journaling files created
# by SQLite. This folder should be overloaded by a volume
# mount in production, but serves as fallback this is not configured.
USER root
RUN apk add openssl
RUN mkdir -p /source/ /certs/ &&\
    chmod a+rw -R /source /certs /var/lib/pgadmin

# Add entrypoint script for container init.
COPY ./entrypoint.sh /source/
ENTRYPOINT ["sh","/source/entrypoint.sh"]
