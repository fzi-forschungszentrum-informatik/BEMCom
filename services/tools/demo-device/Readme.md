# Demo Device

A service that should behave like a simple Modbus device. This tool is solely intended for demonstration of BEMCom. It has no practical value besides this function.

The demo can be interpreted as as a single room for which the temperature is measured and an actor (say an AC system that can heat and cool) exists to manipulate the room temperature.

The demo device exposes the following registers:

| Type             | Register | Data Type   | Description                                                  |
| ---------------- | -------- | ----------- | ------------------------------------------------------------ |
| Input Register   | 1        | 16bit float | The current room temperature in °C.                          |
| Holding Register | 1        | 16bit float | The setpoint for the room temperature in °C. Values below 15°C and above 30° are clipped to that range. |



### Configuration

##### Ports

| Port | Usage/Remarks                                                |
| ---- | ------------------------------------------------------------ |
| 502  | Container accepts ModbusTCP connections on this port. Use Modbus unit ID 1. |

##### Environment Variables

None.

##### Volumes

None.



### Changelog

| Tag   | Changes                                    |
| ----- | ------------------------------------------ |
| 0.0.1 | Some work in progress development version. |
| 0.1.0 | First productive version.                  |