FROM debian:stable-slim

RUN apt-get update && apt-get install -y --no-install-recommends mosquitto="2.0.11*" && \
    rm -rf /var/lib/apt/lists/*

ADD mosquitto.conf /mosquitto.conf 

ENTRYPOINT [ "mosquitto" ]
CMD [ "-c", "/mosquitto.conf" ]