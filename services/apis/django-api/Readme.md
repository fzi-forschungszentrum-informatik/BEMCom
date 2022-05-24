# Django API

This is the reference implementation for an BEMCom API service.


### Configuration

##### Ports

This service serves plain HTTP only.

**Note:** If the API service should be exposed on the public it is absolutely important to place a reverse proxy like nginx in front of the service to secure the connection with HTTPS.   

| Port | Usage/Remarks                                         |
| ---- | ----------------------------------------------------- |
| 8080 | REST interface and admin user interface on plain HTTP |

##### Environment Variables

| Enironment Variable        | Example  Value                 | Usage/Remarks                                                |
| -------------------------- | ------------------------------ | ------------------------------------------------------------ |
| MQTT_BROKER_HOST           | broker.domain.de               | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST           | 1883                           | The port of the MQTT broker. Defaults to `1883`.             |
| ACTIVATE_CONTROL_EXTENSION | TRUE                           | If set to `TRUE` (the string) will make the additional endpoints (on REST API) and additional configuration options (in Admin UI) available that are required to interact with controllers. In particular this enables the `*setpoint/` and `*schedule` REST endpoints that allow interaction with Schedule and Setpoint messages. Furthermore, the `Controllers`, `Controlled datapoints`, `Datapoint setpoints` and `Datapoint schedule`  pages will be activated in the administration UI. Note that some of these endpoints/pages depend also on ACTIVATE_HISTORY_EXTENSION. Defaults to `FALSE` to keep the interface clean for all those who don't need the controller functionality. |
| ACTIVATE_HISTORY_EXTENSION | TRUE                           | If set to `TRUE` (the string) the API service will record all Value, Setpoint and Schedule Message it receives from the broker in the database. Note that this can be a lot of data, especially for low resource devices like a RaspberryPI. Setting this flag will expose `*value`, `*setpoint`, and `*schedule` REST endpoints to interact with the recorded values. Furthermore, the `Datapoint values`, `Datapoint setpoints` and `Datapoint schedule`  pages will be activated in the administration UI. Note that some of these endpoints/pages also depend on ACTIVATE_CONTROL_EXTENSION. Defaults to `FALSE` to keep the resource usage small and the interface clean by default. |
| LOGLEVEL                   | INFO                           | Defines the log level. Should be one of the following strings: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. See the [Django docs on logging](https://docs.djangoproject.com/en/3.1/topics/logging/) for details. Defaults to `INFO`. |
| DJANGO_DEBUG               | FALSE                          | If set to `TRUE` (the string) will activate the [debug mode of django](https://docs.djangoproject.com/en/3.1/ref/settings/#debug), which should only be used while developing not during production operation. Defaults to False |
| DJANGO_ADMINS              | '["John", "john@example.com"]' | Must be a valid JSON string. Is set to [ADMINS setting](https://docs.djangoproject.com/en/3.1/ref/settings/#admins) of Django. Defaults to an empty list. |
| DJANGO_SECRET_KEY          | oTg2aWkM...                    | Can be used to specify the [SECRET_KEY](https://docs.djangoproject.com/en/3.1/ref/settings/#std:setting-SECRET_KEY) setting of Django. Defaults to a random sequence of 64 chars generated on container startup. Note that changing the secret key will invalidate all cookies and thus force all user to login again. |
| DJANGO_ALLOWED_HOSTS       | ["bemcom.domain.com"]          | A list of fully qualified hostnames the API service should be hosted on. Must be encoded as JSON string. See the [ALLOWED_HOSTS](https://docs.djangoproject.com/en/3.1/ref/settings/#allowed-hosts) setting of Django for details. Defaults to `'["localhost"]'`, which means that API can only be accessed from the local machine. |
| DJANGO_SUPERUSER_USERNAME  | admin                          | If username, password and email is provided will attempt to create a superuser account with these credentials. |
| DJANGO_SUPERUSER_PASSWORD  | pass                           | See above.                                                   |
| DJANGO_SUPERUSER_EMAIL     | admin@example.com              | See above.                                                   |
| DJANGOAPIDB_HOST           | timescaledb.domain.de          | The DNS name or IP address of the TimescaleDB used to persist data. Note that `localhost` will not work, use the full DNS name of the host machine instead. If left empty defaults to use a SQLite with data stored in file source/db.sqlite3 . See [Database Setup](#database-setup) below for details. |
| DJANGOAPIDB_PORT           | 5433                           | The port of the TimescaleDB. Defaults to `5432`.             |
| DJANGOAPIDB_USER           | johndoe                        | The username used for authentication at TimescaleDB. Defaults to `bemcom`. |
| DJANGOAPIDB_PASSWORD       | VerySecret123                  | The password used for authentication at TimescaleDB. Defaults to `bemcom`. |
| DJANGOAPIDB_DBNAME         | bemcom                         | The name of the of the database inside TimescaleDB to store the data in. Defaults to `bemcom` |
| N_MTD_WRITE_THREADS        | 1                              | The number of parallel threads the api_main/mqtt_integration.py MqttToDb class uses to push incomming MQTT messages into the Database. This must be an integer. Defaults to 1 as SQLite DBs don't support parallel read or write operations. For TimescaleDBs Values like 32 or above give a significant increase in write throughput. |
| N_WORKER_PROCESSES         | 16                             | The number of parallel worker processes that are used by the production server (UVicorn) to run the application. A sane number may be roughly 2-4 times the number of cores. Defaults to 1. |
| ROOT_PATH                  | bemcom/                        | Use this if BEMCom is served on a subpath behind a reverse proxy. |
| HTTPS_ONLY                 | TRUE                           | If set to `TRUE` (the string) the API will serve cookies over https only. |


##### Volumes

None for most scenarios. Eventually a volume may be used to persist the SQLite database file. See below.



### Database Setup

The Django API service is intended to use a [TimescaleDB](https://docs.timescale.com/timescaledb/latest/) to persist data, which allows good performance even if larger number of datapoint value/setpoint/schedule messages are stored.

##### TimescaleDB

No special configuration of TimescaleDB is necessary to use it with the Django API service. See the [docker-compose.yml](docker-compose.yml) file of the service for an example how to start a Timescale Container. See also the [TimescaleDB documentation](https://docs.timescale.com/timescaledb/latest/) for further details. 

##### SQLite

SQLite database are not recommended for production use. No setup is required for just testing the container. 

**Please note**: Some features of the Django API do not work while using SQLite. In particular this is holds for the interval parameter of the GET /datapoint/{dp-id}/value/ of the REST API endpoint, as well as any other features that uses TimescaleDBs time_bucket to aggregate data to desired intervals.

If the SQLite file should be persisted beyond the container life it is necessary to carry out the following steps:

* ```bash
  # Create an empty file so docker has something to mount
  touch /source/db.sqlite3
  ```

* Add the following line to the docker-compose file:

  ```
          volumes:
              - ./source/db.sqlite3:/source/db.sqlite3
  ```

##### Initialize the Database

If you have added a clean new database you need to initialize the database.

* If you develop locally you need to apply the migrations to create the required tables and layout. To do so execute:

  ```bash
  source/api/manage.py migrate
  ```
  
  Note: This is done automatically if you start up the API container.
  
* To create the Admin user (that you need to login into the AdminUI) use:

  * For local development:

    ```bash
    source/api/manage.py createsuperuser
    ```

  * While running in the container:

    ```bash
    docker exec -it django-api /source/api/manage.py createsuperuser
    ```



### Backup & Restore

**Starting from version 0.2.7** this container integrates a script to backup datapoint metadata and datapoint messages stored in the metadata database. The process uses the REST API and can thus be carried out from remote and is independent of the actual database used.

The command reference of the corresponding script can be displayed with (on bash):

```bash
docker run bemcom/django-api:<tag_of_target_django-api> python /source/api/ems_utils/simple_db_backup.py --help
```

An example that backs up the data of 2021-08-01 to the current working directory is the following command (on bash):

```bash
docker run --rm -v ${PWD}:/data -u "$(id -u):$(id -g)" --name django-db-backup bemcom/django-api:<tag_of_target_django-api> python /source/api/ems_utils/simple_db_backup.py -b -t <URL_of_target_django-api> -s 2021-08-01 -e 2021-08-01 -d /data/ -u <username_at_target_django-api> -p <username_at_target_django-api>
```



### Development Checklist

Follow the following steps while contributing to the connector:

* Create a `.env` file with suitable configuration for your local setup. It is usually a good idea to set the `DEBUG=TRUE` and `LOGLEVEL=DEBUG` for developing.

* If you have no Database set up yet, follow the steps of [Database Setup](#database-setup) above.

* For local development (the code is executed in a python environment on the machine):

  * Install dependencies with:

    ```bash
    pip install -r ./source/requirements.txt
    ```

  * Define a an export temporary directory for Prometheus exporter (see [here](https://github.com/prometheus/client_python#multiprocess-mode-eg-gunicorn) for details).
    
    ```bash
    export PROMETHEUS_MULTIPROC_DIR="$(mktemp -d)"
    ```
    
  * Start the MqttToDb process if needed with:
    
    ```bash
    source/api/manage.py mqtttodb
    ```
    
  * Start the development server if needed with: 
    
    ```bash
    source/api/manage.py runserver
    ```
    
  * Implement your changes as well all tests to cover your changes.
  
  * To run the tests use (check the [pytest docs](https://docs.pytest.org/en/stable/contents.html) for more information):
  
    ```bash
    pytest source/api/
    ```
  
* For development in the container (use `MODE=DEVL` in `.env` file for debug log output and to enable [nice features of Django](https://docs.djangoproject.com/en/3.1/ref/settings/#debug)):

  * Start the container with:

    ```bash
    docker-compose up
    ```

  * Implement your changes as well all tests to cover your changes.

  * To run the tests use the following line in a second terminal (check the [pytest docs](https://docs.pytest.org/en/stable/contents.html) for more information):

    ```bash
    docker exec django-api pytest /source/api/
    ```

* After everything is ready check that service also works in production mode by executing:

  ```bash
  DJANGO_DEBUG=FALSE docker-compose up --build
  ```

* Update the tag (version) in [source/api/api_main/settings.py](source/api/api_main/settings.py) and execute the shell script to build an updated image.

    ```bash
    # This will fail if not all tests are passed.
    bash build_docker_image.sh
    ```

* Document your changes and new tag by appending the list below.

* git add, commit and push.



### Changelog

| Tag   | Changes                                                      |
| ----- | ------------------------------------------------------------ |
| 0.1.0 | Initial functional version                                   |
| 0.2.0 | Massive performance improvement for handling MQTT messages.<br />Extend REST Interface to allow importing Datapoint metadata from JSON.<br />Improve display of Datapoints in AdminUI. |
| 0.4.0 | Datapoint Value and Available Datapoint messages and a can now contain any JSON data type as value. |
| 0.5.0 | Transition to TimescaleDB. Datapoint value messages can now be resampled to intervals (operation happens in DB) with REST parameter. Restore function implemented.<br />**Note: this is a breaking update. All data must be backed up manually before upgrading to this version and restored manually afterwards.** |
| 0.6.0 | Django-API service now exposes Prometheus metrics to support monitoring of BEMCom applications. |
| 0.7.0 | Django-API service can now be run with multiple worker processes. Added dedicated process to write MQTT messages to DB. Removed support for direct HTTPS endpoint (not supported by Gunicorn). |
| 0.8.0 | Added ACTIVATE_CONTROL_EXTENSION and ACTIVATE_HISTORY_EXTENSION flags. |

