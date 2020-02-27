FROM nodered/node-red:1.0.3-4

USER root
RUN apk add jq
USER node-red


COPY Node-RED_data /data

COPY --chown=1000:1000 docker-entrypoint.sh /usr/local/bin/
RUN chmod u+x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
