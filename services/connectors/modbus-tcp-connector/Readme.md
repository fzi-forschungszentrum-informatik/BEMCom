# Modbus TCP Connector

This is a connector to communicate with Devices over ModbusTCP. A short introduction to Modbus can e.g. be found [here](https://www.csimn.com/CSI_pages/Modbus101.html).

The following Modbus function codes are currently supported:

| Modbus Function Code | Name                  |
| -------------------- | --------------------- |
| 3                    | Read holding register |
| 4                    | Read input register   |

The following Modbus function codes are planned for future support:

| Modbus Function Code | Name                          |
| -------------------- | ----------------------------- |
| 1                    | Read coil                     |
| 2                    | Read discrete input           |
| 5                    | Write single coil             |
| 6                    | Write single holding register |



### Supported Devices/Gateways

This connector should be able to communicate with any Modbus Device or Gateway. The following devices have been explicitly tested:

| Manufacturer | Model      | Tested?/Remarks? |
| ------------ | ---------- | ---------------- |
| Janitza      | UMG-96RM-E | Tested.          |



### Configuration

##### Environment Variables

| Enironment Variable       | Example  Value                   | Usage/Remarks                                                |
| ------------------------- | -------------------------------- | ------------------------------------------------------------ |
| CONNECTOR_NAME            | modbus-tcp-connector-device-name | The name of the connector. Must be unique and is used to compute the MQTT topics. Use all lowercase chars and only dashes for separation to prevent clashes with Dockers internal name resolution system. |
| MQTT_BROKER_HOST          | broker.domain.de                 | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST          | 1883                             | The port of the MQTT broker.                                 |
| SEND_RAW_MESSAGE_TO_DB    | TRUE                             | If set to `TRUE` (that is a string of capital letters) will publish all received raw messages on topic `${CONNECTOR_NAME}/raw_message_to_db` |
| DEBUG                     | TRUE                             | If == "TRUE" (i.e. the string) will set the loglevel of the connector the logging.DEBUG. Else is logging.INFO. |
| POLL_SECONDS              | 30                               | The period of polling the Modbus device/gateway for sensor datapoints. |
| MODBUS_MASTER_IP          | 192.168.0.1                      | The ip adress or DNS name of the Modbus master device which we want to connect to. |
| MODBUS_MASTER_PORT        | 502                              | The port on which  the master device awaits Modbus communication. |
| MODBUS_CONFIG             | see below.                       | see below.                                                   |
| MODBUS_MAX_RETRIES        | 3                                | Maximum number of retrying a failed read/write operation before the connector shuts down with an error. Default value is 3. |
| MODBUS_RETRY_WAIT_SECONDS | 15                               | Wait time in seconds after a failed read/write operation before trying again. Defaults to 15 seconds. |

The MODBUS_CONFIG allows to specify which registers should be read out by the connector as well as how to parse the values.

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
    "read_discrete_inputs": [],
    "read_holding_registers": [],
    "read_input_registers": [
        {
            "address": 19000,
            "count": 20,
            "unit": 1,
            "datatypes": ">ffffffffff",
            "scaling_factors": {
                "19002": 0.1
            }
        }
    ]
}
```

The keys on the first level (e.g. `read_holding_registers`) specify the Modbus functions that should be used to interact with the device. Modbus functions that are not used at all (e.g. `read_holding_registers`  here) can be omitted.

It is possible to define several ranges per function, here only one range is defined for `read_input_registers`. Each range item is an object containing the keys `address`, `count` and `unit`. These keywords are forwarded to the corresponding [pymodbus method](https://pymodbus.readthedocs.io/en/latest/source/library/pymodbus.client.html) used for communication using the appropriate Modbus function. Here `address` is the start address, i.e. the first Modbus address that is requested. `count` specifies how many registers/coils are requested. `unit` corresponds to the Modbus unit number, which allows to communicate with several devices through a Modbus master gateway. Finally, the `datatypes` string is only applicable to registers and specifies how the bytes should be parsed, it must be a valid [struct format string](https://docs.python.org/3/library/struct.html#format-strings).

In the example above 20 input registers starting at address 19000 are read out by the connector from a Modbus device that has the id 1. From the device manual it is known that the registers of interest hold 10 32bit float values in big-endian encoding, the `datatypes` format string is set accordingly. Furthermore the value on register number 19002 is scaled (i.e. multiplied with) a factor of 0.1 before it is published on the broker. 

The `read_coils` example above requests 8 bits starting (and including) address 10.

##### Volumes

None.



### Development Checklist

Follow the following steps while contributing to the connector:

* Update the `.env` file with suitable configuration for your local setup.

* Specify all required dependencies in [source/requirements.txt](source/requirements.txt).

* Optional: Install a local version of dependencies for local development:

  * ```bash
    # in service_templates/connectors/Python/
    pip install ./source/
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
| 0.1.0 | First productive version.                                    |
| 0.2.0 | Can read coils and discrete inputs now and allows application of scaling factors. |