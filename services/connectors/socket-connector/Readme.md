# Socket Connector

This is a connector that allows receiving messages that are published by a device or gateway on a socket. It is not designed to pull information, as the latter usually requires more device/gateway specific interaction for which it very likely more simple to to develop a custom connector then handling every special case here. Currently only TCP is implemented. 



### Supported Devices/Gateways

This should work with any device or machine that implements standard TCP and uses it to publish information. 



### Configuration

##### Ports

None.

##### Environment Variables

| Enironment Variable    | Example  Value      | Usage/Remarks                                                |
| ---------------------- | ------------------- | ------------------------------------------------------------ |
| CONNECTOR_NAME         | brand-new-connector | The name of the connector. Must be unique and is used to compute the MQTT topics. Use all lowercase chars and only dashes for separation to prevent clashes with Dockers internal name resolution system. |
| MQTT_BROKER_HOST       | broker.domain.de    | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST       | 1883                | The port of the MQTT broker.                                 |
| SEND_RAW_MESSAGE_TO_DB | TRUE                | If set to `TRUE` (that is a string of capital letters) will publish all received raw messages on topic `${CONNECTOR_NAME}/raw_message_to_db` |
| DEBUG                  | TRUE                | If == "TRUE" (i.e. the string) will set the loglevel of the connector the logging.DEBUG. Else is logging.INFO. |
| SERVER_IP              | 192.168.0.55        | The DNS name or IP address of the target device or gateway.  |
| SERVER_PORT            | 587                 | The port which the connector should connect to on the target device or gateway. |
| RECV_BUFSIZE           | 1024                | The buffersize used while receiving information. The data from the device or gateway should not exceed this many bytes as the raw message will else be split up and may end up unreadable. See also the [socket docs](https://docs.python.org/3/library/socket.html) for more information. Defaults to 4096. |
| RECV_TIMEOUT           | 15                  | Max wait time before a message is expected. Will shutdown connector if no message is received after that time (to allow a restart and reconnection). 0 means we expect a message immediately (non-blocking mode). Negative values wait as long as possible (blocking mode). See [here](https://docs.python.org/3/library/socket.html#socket-timeouts) for details. |
| PARSE_AS               | YAML                | Defines how the raw data should be parsed as objects. Either YAML or JSON is supported. Defaults to JSON. |

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

* Update the version number (aka. the tag) in [source/connector/main.py](./source/connector/main.py) before building the docker image. 

* Execute [./build_docker_image.sh](./build_docker_image.sh) to build an updated image. 

  ```bash
  # This will fail if not all tests are passed.
  bash build_docker_image.sh
  ```

* Document your changes and new tag by appending the list below.

* git add, commit and push.



### Changelog

| Tag   | Changes                                                      |
| ----- | ------------------------------------------------------------ |
| 0.1.0 | First productive version.                                    |
| 0.4.0 | Update to python connector template 0.4.0 (Datapoint Value and Available Datapoint messages and a can now contain any JSON data type as value.) |
| 0.5.0 | Add timeout to allow automatic restarts if connection is lost. |