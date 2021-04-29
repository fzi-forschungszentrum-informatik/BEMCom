# KEBA P30 Connector

This is a connector to integrate the [KEBA P30 charge station](https://www.keba.com/de/emobility/products/product-overview/produktubersicht).

The Connector uses the UDP interface specified [here](https://www.keba.com/download/x/4a925c4c61/kecontactp30udp_pgen.pdf).

This connector allows to integrate multiple P30 charge stations with one connector, which is in contrast to the general BEMCom design principle to use one connector per network address. However, as this connector must bind port 7090 to receive responses there can be only one connector at a time.



### Supported Gateways

No gateway, the charge station communicated directly via Ethernet.



### Supported Devices

The following devices have been tested 

| Manufacturer | Model                             | Tested?/Remarks? |
| ------------ | --------------------------------- | ---------------- |
| KEBA         | P30 charge station.               | Tested.          |



### Configuration

##### Ports

| Port                    | Usage/Remarks                                                |
| ----------------------- | ------------------------------------------------------------ |
| 7090 | UDP Port used by the charge station to receive and send messages. The charge station insists on sending the messages back on exactly this port. |

##### Environment Variables

| Enironment Variable      | Example  Value                   | Usage/Remarks                                                |
| ------------------------ | -------------------------------- | ------------------------------------------------------------ |
| CONNECTOR_NAME           | brand-new-connector              | The name of the connector. Must be unique and is used to compute the MQTT topics. Use all lowercase chars and only dashes for separation to prevent clashes with Dockers internal name resolution system. |
| MQTT_BROKER_HOST         | broker.domain.de                 | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST         | 1883                             | The port of the MQTT broker.                                 |
| SEND_RAW_MESSAGE_TO_DB   | TRUE                             | If set to `TRUE` (that is a string of capital letters) will publish all received raw messages on topic `${CONNECTOR_NAME}/raw_message_to_db` |
| DEBUG                    | TRUE                             | If == "TRUE" (i.e. the string) will set the loglevel of the connector the logging.DEBUG. Else is logging.INFO. |
| POLL_SECONDS           | 30                               | The period of polling the P30 charge stations. |
| KEBA_P30_CHARGE_STATIONS | '{"p30_garage": "192.168.0.99"}' | A JSON dictionary containing names and ip addresses (or DNS names) of P30 charge stations. This defines which charge stations should be polled for data. Must be set. |

##### Volumes

None.



### Development Checklist

Follow the following steps while contributing to the connector:

* Update the `.env` file with suitable configuration for your local setup.

* Specify all required dependencies in [source/requirements.txt](source/requirements.txt).

* Optional: Install a local version of dependencies for local development:

  * ```bash
    # in service_templates/connectors/Python/
    pip install -e ./source/
    ```

  * ```bash
    # in the folder of your connector
    pip install -r ./source/requirements.txt
    ```

* Place your code under [source/connector](./source/connector) but keep the [source/connector/main.py](./source/connector/main.py) as entrypoint. Place your tests in [source/connector/tests](./source/connector/tests).

* Ensure all relevant tests exist and all of those are passed before preceding. 

* Update the image name and tag in  [./build_docker_image.sh](./build_docker_image.sh) and execute the shell script to build an updated image. 

  ```bash
  # This will fail if not all tests are passed.
  bash build_docker_image.sh
  ```

* Document your changes and new tag by appending the list below.

* git add, commit and push.



### Changelog

| Tag   | Changes                                                      |
| ----- | ------------------------------------------------------------ |
| 0.1.0 | Initial version                                              |
| 0.2.0 | Switch from Node-RED template to Python template to frequent connection losses due to the charge station ignoring the source port of the UDP message. |
| 0.3.0 | Add functionality to write actuator values to charge station. |