# Modbus/TCP Connector

This is a connector to communicate with Devices over Modbus/TCP. A short introduction to Modbus can e.g. be found [here](https://www.csimn.com/CSI_pages/Modbus101.html).

The following Modbus function codes are supported:

| Modbus Function Code | Name                             |
| -------------------- | -------------------------------- |
| 1                    | Read coil                        |
| 2                    | Read discrete input              |
| 3                    | Read holding register            |
| 4                    | Read input register              |
| 5                    | Write single coil                |
| 6                    | Write single holding register    |
| 16                   | Write multiple holding registers |



### Supported Devices/Gateways

This connector should be able to communicate with any Modbus Device or Gateway. The following devices have been explicitly tested:

| Manufacturer | Model      | Tested?/Remarks? |
| ------------ | ---------- | ---------------- |
| Janitza      | UMG-96RM-E | Tested.          |



### Configuration

##### Environment Variables

| Enironment Variable             | Example  Value                   | Usage/Remarks                                                |
| ------------------------------- | -------------------------------- | ------------------------------------------------------------ |
| CONNECTOR_NAME                  | modbus-tcp-connector-device-name | The name of the connector. Must be unique and is used to compute the MQTT topics. Use all lowercase chars and only dashes for separation to prevent clashes with Dockers internal name resolution system. |
| MQTT_BROKER_HOST                | broker.domain.de                 | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST                | 1883                             | The port of the MQTT broker.                                 |
| SEND_RAW_MESSAGE_TO_DB          | TRUE                             | If set to `TRUE` (that is a string of capital letters) will publish all received raw messages on topic `${CONNECTOR_NAME}/raw_message_to_db` |
| DEBUG                           | TRUE                             | If == "TRUE" (i.e. the string) will set the loglevel of the connector the logging.DEBUG. Else is logging.INFO. |
| POLL_SECONDS                    | 30                               | The period of polling the Modbus device/gateway for sensor datapoints. |
| MODBUS_MASTER_IP                | 192.168.0.1                      | The ip adress or DNS name of the Modbus master device which we want to connect to. |
| MODBUS_MASTER_PORT              | 502                              | The port on which  the master device awaits Modbus communication. |
| MODBUS_CONFIG                   | see below.                       | see below.                                                   |
| MODBUS_MAX_RETRIES              | 3                                | Maximum number of retrying a failed read/write operation before the connector shuts down with an error. Default value is 3. |
| MODBUS_RETRY_WAIT_SECONDS       | 15                               | Wait time in seconds after a failed read/write operation before trying again. Defaults to 15 seconds. |
| MODBUS_POLL_BREAK               | 0.1                              | Wait time in seconds between two consecutive requests. Some devices react with errors if getting polled too often. Defaults to 0.0 |
| MODBUS_DISCONNECT_BETWEEN_POLLS | TRUE                             | If == "TRUE" (i.e. the string) will disconnect from Modbus master device between polls. This is useful for devices that can only handle a single connection or that react with errors if POLL_SECONDS is larger then a few seconds. Defaults to FALSE. |

The MODBUS_CONFIG allows to specify which registers should be read out or written to by the connector as well as how to parse the values.

A JSON string is expected that is is structured like this:

```json
{
    "read_coils": [
        {
            "address": 10,
            "count": 8,
            "unit": 1,
        }
    ],
    "read_discrete_inputs": [], # Similar to "read_coils"
    "read_holding_registers": [
        {
            "address": 19000,
            "count": 20,
            "unit": 1,
            "datatypes": ">ffffffffff",
            "scaling_factors": {
                "19002": 0.1
            }
        }
    ],
    "read_input_registers": [], # Similar to "read_coils"
    "write_coil": [
        {
            "address": 10,
            "unit": 1,
            "example_value": "true"
        }
    ],
    "write_register": [
        {
            "address": 19000,
            "unit": 1,
            "datatypes": ">h",
            "example_value": "22"
        }
    ],
    "write_registers": [
        {
            "address": 19001,
            "unit": 1,
            "datatypes": ">f",
            "example_value": "21.0"
        }
    ]
}
```

The keys on the first level (e.g. `read_holding_registers`) specify the Modbus functions that should be used to interact with the device. Modbus functions that are not used at all (e.g. `read_input_registers`  here) can be omitted.

It is possible to define several ranges per function, here only one range is defined for `read_input_registers`. Each range item is an object containing keys. The following table defines which keys must be provided per modbus function.

| Key               | Applicable to functions                          | Explanation                                                  |
| ----------------- | ------------------------------------------------ | ------------------------------------------------------------ |
| `address`         | all                                              | Specifies the start address, i.e. the first Modbus address that is requested. |
| `count`           | `read_*`                                         | Specifies how many registers/coils are requested.            |
| `unit`            | all                                              | Corresponds to the Modbus unit number, which allows to communicate with several devices through a Modbus master gateway. |
| `datatypes`       | All that interact with registers                 | Specifies how values are parsed from/to bytes , it must be a valid [struct format string](https://docs.python.org/3/library/struct.html#format-strings). |
| `scaling_factors` | `read_discrete_inputs`, `read_holding_registers` | Allows scaling the values received from the Modbus device before publishing on BEMCom (i.e. multipling the value with the factor). |
| `example_value`   | `write_*`                                        | Defines an example value for display in the API service.     |

The `read_coils` example above requests 8 bits starting (and including) address 10.

In the example above, the range defined under `read_coils`  requests 8 bits starting (and including) address 10 from a Modbus device that has the id 1.

The range under `read_holding_registers` configures the connector to read 20 registers starting at address 19000 from a Modbus device that has the id 1. From the device manual it is known that the registers of interest hold 10 32bit float values in big-endian encoding, the `datatypes` format string is set accordingly. Furthermore the value on register number 19002 is scaled (i.e. multiplied with) a factor of 0.1 before it is published on the broker.

The range under `write_coil` specifies that a single Bool can be written to coil 10 of Modbus device with id 1. The example value is the boolean value True.

The range under `write_register` specifies that a single integer can be written to register 19000 of Modbus device with id 1. The example value is 22.

The range under `write_registers` specifies that a single float can be written to registers 19001 and 19002. This is as the value of `datatypes` defines a float 32 in big-endian encoding, which will thus span two registers. How many registers are affected is determined automatically based on the data type. Again the value is written a Modbus device with id 1 and the example value is 21.0.

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
| 0.2.0 | Can read coils and discrete inputs now and allows application of scaling factors. |
| 0.3.0 | Allow disconnecting between polls and breaks between requests in one poll run. |
| 0.4.0 | Update to python connector template 0.4.0 (Datapoint Value and Available Datapoint messages and a can now contain any JSON data type as value.) |
| 0.5.0 | Connector can now write to coils and registers. Unit id is now part of the internal datapoint id to prevent collisions while interacting with the same addresses from different devices. |
| 0.6.0 | Update to python connector template 0.5.0 (It is now possible to stop processing messages in run_sensor_flow.) |

