# MQTT Message Monitor

This service allows you to inspect the MQTT messages exchanged in an application. It will show the last message per topic. The monitoring tool is implemented in Node-RED.



### Configuration

##### Ports

| Port | Usage/Remarks                                                |
| ---- | ------------------------------------------------------------ |
| 1880 | Node-RED development user interface. Also provides the user interface under /ui/ |

##### Environment Variables

| Enironment Variable         | Example  Value      | Usage/Remarks                                                |
| --------------------------- | ------------------- | ------------------------------------------------------------ |
| MQTT_BROKER_HOST            | broker.domain.de    | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_PORT            | 1883                | The port of the MQTT broker.                                 |

##### Volumes

| Path in Container | Usage/Remarks                                                |
| ----------------- | ------------------------------------------------------------ |
| /data             | Holds the Node-RED data. Only use this mount for developing the tool further. |



### Changelog

| Tag   | Changes                                                  |
| ----- | -------------------------------------------------------- |
| 0.1.0 | Initial version.                                         |