FROM mongo:4.2-bionic

# Install python3 and dependencies for the 
# apt-get install python3-pip will take roughly 350MB of diskspace.
# Thus remove the package after we have installed the MQTT client.
RUN apt-get update &&\
    apt-get install -y python3-minimal python3-pip &&\
    pip3 install paho-mqtt==1.5 pymongo==3.10 &&\
    apt-get remove -y python3-pip &&\
    apt-get -y autoremove

COPY mqtt_integration.py /bemcom/
COPY entrypoint.sh /bemcom/

CMD ["bash","/bemcom/entrypoint.sh"]
