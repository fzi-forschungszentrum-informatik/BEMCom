# Creating BEMCom Applications

Recalling the [application concept](./01_concepts.md), it is apparent that a functional and building specific HAL instance will require one API service (including the metadata database), one message broker, one or more connector services, and optionally a raw message database service. The BEMCom repository provides fully functional implementations of an API service, a message broker and a raw message database which should be sufficient for most applications, thus effectively removing the burden of implementing these services from the user. It is worth noting that the provided implementation of the API service exposes a secure REST interface for external components, supporting user authentication and HTTPS for encryption. All available services, including a number of connector services, can be found in the [services](../services/) folder in this repository.

Leveraging the design concepts of BEMCom, i.e. the service oriented approach and the execution of services as Docker containers, creating an application is reduced to simply configuring and starting the selected services.



## Creating Applications with Docker

This is a minimal example showing how a functional BEMCom application can be created by manually starting each service via a shell command, which should work on any machine having docker installed. Please note that the more convenient way to achieve the same result by utilizing Docker Compose is subject to the following section.

In order to demonstrate the full functionality of BEMCom it is certainly necessary to begin with a device to communicate with. To that end we provide a [Demo Device](../services/tools/demo-device/Readme.md) service reflecting a simple Modbus device which can be interpreted as as a single room for which the temperature is measured and an actor (say an AC system that can heat and cool) exists to manipulate the room temperature. However before the first service is started it is necessary to create a docker network to allow communication between the services.

```bash
docker network create bemcom-demo
```

After the Docker network exists now, it is possible to start the Demo Device with:

```bash
docker run -d --network bemcom-demo --name bemcom-demo-device bemcom/demo-device-tool:0.1.0
```

Here the `-d` flag will cause docker to run the Demo Device in the background, `--network bemcom-demo` will connect the container to the previously created network and  `--name bemcom-demo-device` will assign the network name `bemcom-demo-device` to the container. To confirm that the service has created successfully execute:

```bash
docker logs bemcom-demo-device
```

Which create an output similar to this one:

```
docker-entrypoint.sh: Starting up
2022-02-03 09:06:04,884-run-INFO: Current temperature: 21.0
```



Recalling the [application concept](./01_concepts.md), it is evident that each BEMCom application requires a central message broker service which to allow the remaining services to communicate with each, which can be launched using the following command:

```bash
docker run -d --network bemcom-demo --name bemcom-demo-mqtt-broker bemcom/mosquitto-mqtt-broker:0.1.0
```
Checking the container logs with `docker logs bemcom-demo-mqtt-broker` indicates the correct operation by displaying:

```
1643880100: mosquitto version 1.6.10 starting
1643880100: Config loaded from /mosquitto/config/mosquitto.conf.
1643880100: Opening ipv4 listen socket on port 1883.
1643880100: Opening ipv6 listen socket on port 1883.
```



In order to establish communication between the Demo Device and the message broker it is necessary to spin up the corresponding connector, in this particular case that is the [Modbus/TCP connector](../services/connectors/modbus-tcp-connector/Readme.md) provided in the BEMCom repository, by typing:

```bash
docker run -d --network bemcom-demo --name bemcom-demo-modbus-tcp-connector -e MQTT_BROKER_HOST=bemcom-demo-mqtt-broker -e MQTT_BROKER_PORT=1883 -e CONNECTOR_NAME=bemcom-demo-modbus-tcp-connector -e MODBUS_MASTER_IP=bemcom-demo-device -e MODBUS_MASTER_PORT=502 -e POLL_SECONDS=5 -e MODBUS_CONFIG='{"read_input_registers": [{"address": 1,"count":1,"unit": 1,"datatypes": "e"}],"write_register": [{"address": 1,"unit": 1,"datatypes": "<e","example_value": "22.0"}]}' bemcom/modbus-tcp-connector:0.5.0
```

Albeit this shell command may look far more complex then the ones introduced above, it is actually very similar. The only difference is that the connector service is additionally configured via environment variables, that is what follows `-e`, to account for specific settings of the device and the application. In particular these variables can be interpreted as:

* `MQTT_BROKER_HOST=bemcom-demo-mqtt-broker`: Configures that the connector should connect to the MQTT broker with the network name `bemcom-demo-mqtt-broker`, i.e. the name that is been configured in the command above.
* `MQTT_BROKER_PORT=1883`: Specifies that the MQTT broker expects a connection on port `1883`, that is the default value for MQTT.
* `CONNECTOR_NAME=bemcom-demo-modbus-tcp-connector`: Defines the internal name (i.e. the root topic) as  `bemcom-demo-modbus-tcp-connector` for the information exchange on the broker between the connector and other services.
* `MODBUS_MASTER_IP=bemcom-demo-device`: Specifies the network name or IP address of the Modbus/TCP device that the connector will attempt to communicate with to `bemcom-demo-device`, i.e. the name that is been configured in the command above.
*  `MODBUS_MASTER_PORT=502`: Defines that device expects connections on port `502`, that is the default value for Modbus/TCP.
* `POLL_SECONDS=5`: Declares that the connector should request the configured sensor values (see below) every five seconds by polling the device.
* `MODBUS_CONFIG='{"read_input_registers": ... }'`: Configures the Modbus registers which the connector will attempt to read from or write to. In particular, the connector is set up to handle a single sensor datapoint from input register one and can write a single actuator datapoint to holding register one. It is worth noting here that the concept of registers is specific to Modbus and that the information which information is exposed on which register is device specific and usually document in the documentation belonging to the device.

At this point it is important to highlight two important properties about the configuration of BEMCom services via environment variables:

1. It is solely necessary to change the environment variables to adapted a BEMCom service for a particular application or to a specific device. If one would need to connect a second different Modbus device to the demo application above for example, it is intended to use the same image of the Modbus/TCP connector with adjusted environment variables. It is thus possible to very quickly establish connection to even larger numbers of devices if a suitable connector exists.
2. That which environment variables are available varies per BEMCom service and that a documentation about how to configure each service utilizing those variables is provided in the documentation of the services. Regarding the current example, the documentation of the [Modbus/TCP connector](../services/connectors/modbus-tcp-connector/Readme.md) provides additional details for each environment variables including e.g. extensive discussion how to define the `MODBUS_CONFIG` variable correctly.

Before moving on it is again a good idea to verify the correct operation of the connector by inspecting the logs with `docker logs bemcom-demo-modbus-tcp-connector`, which should yield an output similar to:

```
2022-02-03 11:22:19,416-_get_stream-INFO: Python-dotenv could not find configuration file .env.
2022-02-03 11:22:19,416-parse_modbus_config-INFO: Parsing MODBUS_CONFIG.
2022-02-03 11:22:19,417-_get_stream-INFO: Python-dotenv could not find configuration file .env.
2022-02-03 11:22:19,417-__init__-INFO: Initiating pyconnector.Connector class for: bemcom-demo-modbus-tcp-connector
2022-02-03 11:22:19,417-__init__-INFO: Changing log level to INFO
2022-02-03 11:22:19,421-run-INFO: Connector online. Entering main loop.
```



<p style="color:red;">TODO: Add details about how to add the API service.</p>



<p style="color:red;">TODO: Add note about Play with docker.</p>



<p style="color:red;">TODO: Add details about how to stop the containers and remove the network and the containers.</p>



## Creating Applications with Docker Compose'



<p style="color:red;">TODO: Add docker compose file that exactly matches the example above.</p>



<p style="color:red;">TODO: Also add docker compose file that reflects the usual settings.</p>
