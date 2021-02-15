# Django based API

* Security issues are monitored and new versions of this API are provided asap if a security issue in one of the components becomes known.

# Homematic Connector

This is a connector to integrate [eQ-3 Homematic](https://www.eq-3.com/products/homematic.html) devices.

### To document:

* [ ] Mounts for DB
* [ ] SECRET_KEY
* [ ] ALLOWED_HOSTS? -> Rather Host FQDN
* [ ] ADMIN
* [ ] `MODE=PROD SSL_KEY_PEM=$(cat key.pem) SSL_CERT_PEM=$(cat cert.pem) docker-compose up --build`
* [ ] docker exec -it django-api /bemcom/code/manage.py createsuperuser

### TODO

* [ ] E-Mail Backend?

### Supported Gateways

| Manufacturer | Model                              | Tested?/Remarks?                      |
| ------------ | ---------------------------------- | ------------------------------------- |
| eQ-3         | Homematic CCU3 (HmIP-CCU3)         | Tested.                               |
| eQ-3         | Homematic CCU2 (HM-Cen-O-TW-x-x-2) | Not tested, should nevertheless work. |



### Supported Devices

The connector should be able to process sensor datapoints of all existing Homematic devices. Currently only actuator datapoints of parameter type `SET_TEMPERATURE` are recognized automatically and exposed as available datapoints. The following devices have been tested 

| Manufacturer | Model                              | Tested?/Remarks?                                             |
| ------------ | ---------------------------------- | ------------------------------------------------------------ |
| eQ-3         | Wall Thermostat (HM-TC-IT-WM-W-EU) | Tested, also writing the `SET_TEMPERATURE` datapoint. Pushing values other then allowed range (5-30.5°C) to `SET_TEMPERATURE` will result in an `off` setpoint. |
| eQ-3         | Window Handle Sensor (HM-Sec-RHS)  | Tested.                                                      |
| eQ-3         | Heating Actuator (HM-CC-RT-DN)     | Tested.                                                      |



### Configuration

##### Ports

| Port                    | Usage/Remarks                                                |
| ----------------------- | ------------------------------------------------------------ |
| 1880                    | Node-RED development user interface.                         |
| ${CALLBACK_BINRPC_PORT} | The external port the CCU will try to connect to for the BINRPC protocol. Should be identical for the host as internal for the container. |
| ${CALLBACK_XMLRPC_PORT} | The external port the CCU will try to connect to for the XMLRPC protocol. Should be identical for the host as internal for the container. |

##### Environment Variables

| Enironment Variable    | Example  Value      | Usage/Remarks                                                |
| ---------------------- | ------------------- | ------------------------------------------------------------ |
| CONNECTOR_NAME         | brand-new-connector | The name of the connector. Must be unique and is used to compute the MQTT topics. Use all lowercase chars and only dashes for separation to prevent clashes with Dockers internal name resolution system. |
| MQTT_BROKER_HOST       | broker.domain.de    | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST       | 1883                | The port of the MQTT broker.                                 |
| SEND_RAW_MESSAGE_TO_DB | TRUE                | If set to `TRUE` (that is a string of capital letters) will publish all received raw messages on topic `${CONNECTOR_NAME}/raw_message_to_db` |
| CCU_DNS_NAME           | ccu.domain.de       | The DNS name or IP address of the CCU to connect to.         |
| CALLBACK_DNS_NAME      | hostname.domain.de  | The DNS name or IP of the machine the connector is run on. Is used by the CCU to connect and push updates. |
| CALLBACK_BINRPC_PORT   | 2069                | See ports. Must be identical to the port exposed on the host to allow the Node-RED flow to send the correct port value to the CCU for callback. |
| CALLBACK_XMLRPC_PORT   | 2070                | See ports. Must be identical to the port exposed on the host to allow the Node-RED flow to send the correct port value to the CCU for callback. |

##### Volumes

None.



### Development Checklist

Follow the following steps while contributing to the connector:

* Create a `.env` file with suitable configuration for your local setup.
* Optional: Update the image of the node-red-connector-template by editing [source/Dockerfile](source/Dockerfile) 
* Start the development instance with  `docker-compose up -d`
* Edit the flows, ensure everything works as expected.
* Export the changed flows and update/create the files in [./source/flows/](./source/flows/). The filenames should be the flows ids.
* Update the image tag in  [./build_docker_image.sh](./build_docker_image.sh) and execute the shell script to build an updated image. 
* Run the new image and check once more everything works as expected.
* Document your changes and new tag by appending the list below.
* git add, commit and push.



### Changelog

| Tag   | Changes                      |
| ----- | ---------------------------- |
| 0.1.0 | Initial version              |
| 0.1.1 | Fix bug in send command flow |