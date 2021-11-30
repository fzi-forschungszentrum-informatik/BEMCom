# Fronius Modbus Connector

This is a Modbus connector specifically for Fronius Symo GEN24 inverters. Manufacturer's information can be found [here](https://www.fronius.com/de/solarenergie/installateure-partner/technische-daten/alle-produkte/anlagen-monitoring/offene-schnittstellen/modbus-tcp?id=a7db8a37-85fb-412d-8c06-9de458400f59).

The reason for this special connector is the requirement to write two registers in order to change the power limit of the inverter (see below).

### TODO

This connector contains a lot of code duplicated from modbus-tcp-connector. It would be better to build the image based on the modbus-tcp-connector image and import these code pieces.

### Supported Devices/Gateways

This connector is made for Fronius Symo GEN24 devices.

| Manufacturer | Model      | Tested/Remarks   |
| ------------ | ---------- | ---------------- |
| Fronius      | Symo Gen24 | Tested.          |


### Configuration

To set the power limit, the following registers have to be written:

| Name        | Type   | Unit                   | Register |
| ----------- | ------ | ---------------------- |----------|
| WMaxLimPct  | uint16 | % of max power (10 kW) | 40242    |
| WMaxLim_Ena | enum16 |                        | 40246    |

When WmaxLimPct is to be written, the given value is multiplied by the scaling factor of 100 and WmaxLim_Ena is set to 1 automatically so you only have to set the desired percentage of the power. If you'd like to control those Modbus registers directly, it is recommended to use the generic Modbus TCP Connector instead.

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
| MODBUS_W_MAX_LIM_PCT            | 40242                            | Register of "WmaxLimPct". Change it if your inverter uses a different one than 40242. Otherwise it can beleft blank |
| MODBUS_W_MAX_LIM_ENA            | 40246                            | Register of "WmaxLim_Ena". Change it if your inverter uses a different one than 40246. Otherwise it can beleft blank |
The MODBUS_CONFIG allows to specify which registers should be read out by the connector as well as how to parse the values.

A JSON string is expected that is is structured like this:

```json
{
    "read_coils": [],
    "read_discrete_inputs": [],
    "read_holding_registers": [
        {
            "address": 40071,
            "count": 46,
            "unit": 1,
            "datatypes":">fffffffffffffffffffffff"
        },
        {
            "address": 40242,
            "count": 1,
            "unit":1,
            "datatypes":">H"
        }

    ],
    "read_input_registers": [],
    "write_coil": [],
    "write_register": [
    {
        "address": 40242,
        "unit": 1,
        "datatypes": ">H",
        "scaling_factor": 100

    },
    {
        "address": 40246,
        "unit": 1,
        "datatypes": ">H",
        "scaling_factor": 1

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

| Tag   | Changes                   |
| ----- | ------------------------- |
| 0.1.0 | First productive version. |
