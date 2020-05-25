# Python Controller

This is a Python based implementation of a Controller service. It listens to all setpoint and schedule messages (see the [message format documentation](./../../../documentation/02_message_format.md) for details) published on the broker, whereby the setpoint reflects the users desired value and the schedule the optimal value computed by an optimization process. Based on these messages the controller computes the value for the actuator datapoint.

The controller ensures the following points:

*  That each item in a setpoint message is executed, as long as the value for `to_timestamp` is not in the past. Executed means thereby that the fields `preferred_value`, and if existing `acceptable_values` or `min_value` and `max_value` are loaded and used while computing the value for the actuator datapoint.
*  That each item in a schedule message is executed, as long as the value for `to_timestamp` is not in the past. Executed means thereby that the field `value`, is loaded and used while computing the value for the actuator datapoint.
* `values` for actuators are only sent if the value changes, to prevent permanently sending the same information to the devices.
* That logic for computing the actuator value at any time are as follows:
  * If neither a setpoint nor a schedule exist the `value` of the actuator will not be changed at all.
  * If no setpoint exists but a schedule, the `value` defined in the schedule will be sent to the actuator.
  * If no schedule exists but a setpoint is, the `preferred_value` of the setpoint message is used as `value` for the actuator. 
  * If setpoint and schedule exist but the datapoint is not of type continuous_numeric or discrete_text/numeric (i.e. the setpoint message contains no flexibility as neither `acceptable_values` or `min_value` and `max_value`  are defined) the schedule message is ignored.
  * If setpoint and schedule exist and the datapoint is of type continuous_numeric (i.e. the fields `min_value` and `max_value` exist) the the `value` of the schedule is sent to the actuator, as least as long as the corresponding sensor datapoint is with the range specified by `min_value` and `max_value`. If the sensor value leaves the allowed range the `preferred_value` is sent as `value` to the actuator.
  * If setpoint and schedule exist and the datapoint is of type discrete (i.e. the field `acceptable_values` exists) the the `value` of the schedule is sent to the actuator, as least as long as the corresponding sensor datapoint is with the range specified by`acceptable_values`. If the sensor value leaves the allowed range the `preferred_value` is sent as `value` to the actuator.



### Configuration

##### Ports

None.

##### Environment Variables

| Enironment Variable              | Example  Value                          | Usage/Remarks                                                |
| -------------------------------- | --------------------------------------- | ------------------------------------------------------------ |
| MQTT_BROKER_HOST                 | broker.domain.de                        | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST                 | 1883                                    | The port of the MQTT broker.                                 |
| MQTT_TOPIC_CONTROLLED_DATAPOINTS | python_controller/controlled_datapoints | The topic on which the controller listens for configuration data. |

##### Volumes

None.



### Changelog

| Tag   | Changes                      |
| ----- | ---------------------------- |
| 0.1.0 | Initial version              |