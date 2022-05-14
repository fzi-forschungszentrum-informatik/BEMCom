# EMP Link

This is a simple tool that automatically pushes new data to the [FZI Energy Management Panel](https://github.com/fzi-forschungszentrum-informatik/energy_management_panel).

### Configuration

##### Ports

None.

##### Environment Variables

| Enironment Variable   | Example  Value             | Usage/Remarks                                                |
| --------------------- | -------------------------- | ------------------------------------------------------------ |
| ORIGIN | EmpLinkTest | The value for the `origin` when pushing datapoints up. |
| AUTO_RELOAD                  | TRUE                            | If `TRUE` (i.e. the string) will host the service with auto reloading enabled, that is, the service restarts if files have changed. This is nice for development but should not be enabled in production. |
| MQTT_BROKER_HOST      | broker.domain.de           | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_PORT  | 18830                      | The port of the MQTT broker. Defaults to `1883`.             |
| BEMCOM_API_URL        | https://bemcom.example.com | The URL of the BEMCom API. Used for fetching the datapoint metadata. |
| BEMCOM_API_VERIFY_SSL | FALSE                      | If == "FALSE" (i.e. the string) will disable certificate checking for the BEMCom API connection. Useful if self signed certificates are used but a potential security risk. See also the [requests docs](https://docs.python-requests.org/en/master/user/advanced/#ssl-cert-verification) on the topic. Defaults to TRUE. |
| BEMCOM_API_USERNAME | jon_doe | The username (HTTP basic auth) to use for connecting to BEMCom API. |
| BEMCOM_API_PASSWORD | verySecret123 | The corresponding password. |
| EMP_API_URL           | https://emp.example.com    | The URL of the EMP API. All new data is pushed there.        |
| EMP_API_VERIFY_SSL    | TRUE                       | Like `BEMCOM_API_VERIFY_SSL` but for the EMP API.            |
| EMP_API_USERNAME | jon_doe | The username (HTTP basic auth) to use for connecting to EMP API. |
| EMP_API_PASSWORD | verySecret123 | The corresponding password. |

##### Volumes

None.



### Development Quick Start

On a Linux system you can start developing on the code quickly by following these steps.

* In a terminal execute:

  ```bash
  docker-compose down -v && USER_ID=$(id -u) GROUP_ID=$(id -g) docker-compose up --build
  ```

* For automatic execution of tests run the following in a second terminal:

  ```bash
  docker exec -it emp-devl auto-pytest /source/emp/
  ```

* For an interactive python terminal execute:

  ```bash
  docker exec -it emp-devl /opt/conda/bin/python /source/emp/manage.py shell
  ```
