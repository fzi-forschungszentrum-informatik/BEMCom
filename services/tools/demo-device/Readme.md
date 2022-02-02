# Demo Device

A service that should behave like a simple Modbus device. This tool is solely intended for demonstration of BEMCom. It has no practical value besides this function.

The demo can be interpreted as as a single roof for which the temperature is measured and an actor (say an AC system that can heat and cool) exist to manipulate the room temperature.  

The demo device exposes the following registers:

| Type             | Number | Description                                                  |
| ---------------- | ------ | ------------------------------------------------------------ |
| Input Register   | 1      | The current room temperature in °C encoded as 16bit float.   |
| Holding Register | 1      | The setpoint for the room temperature also in °C encoded in the same way as the current room temperature. Values below 15°C and above 30° are clipped to those values. |



### Configuration

##### Ports

| Port | Usage/Remarks                                         |
| ---- | ----------------------------------------------------- |
| 502  | Container accepts ModbusTCP connections on this port. |

##### Environment Variables

| Enironment Variable | Example  Value | Usage/Remarks                                                |
| ------------------- | -------------- | ------------------------------------------------------------ |
| DEBUG               | TRUE           | If == "TRUE" (i.e. the string) will set the loglevel of the connector the logging.DEBUG. Else is logging.INFO. |

##### Volumes

None.



### Changelog

| Tag   | Changes                                    |
| ----- | ------------------------------------------ |
| 0.0.1 | Some work in progress development version. |
| 0.1.0 | First productive version.                  |