# Django API

This is the reference implementation for an BEMCom API service.


### Configuration

##### Ports

| Port | Usage/Remarks                                                |
| ---- | ------------------------------------------------------------ |
| 8080 | REST interface and admin user interface on plain HTTP        |
| 8443 | REST interface and admin user interface served securely over HTTPS |

##### Environment Variables

| Enironment Variable | Example  Value                                    | Usage/Remarks                                                |
| ------------------- | ------------------------------------------------- | ------------------------------------------------------------ |
| MQTT_BROKER_HOST    | broker.domain.de                                  | The DNS name or IP address of the MQTT broker. `localhost` will not work, use the full DNS name of the host machine instead. |
| MQTT_BROKER_HOST    | 1883                                              | The port of the MQTT broker.                                 |
| LOGLEVEL            | INFO                                              | Defines the log level. Should be one of the following strings: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. See the [Django docs on logging](https://docs.djangoproject.com/en/3.1/topics/logging/) for details. Defaults to `INFO`. |
| DJANGO_DEBUG        | FALSE                                             | If set to `TRUE` (the string) will activate the [debug mode of django](https://docs.djangoproject.com/en/3.1/ref/settings/#debug), which should only be used while developing not during production operation. Defaults to False |
| DJANGO_ADMINS       | [["John", "john@example.com"]]                    | Must be a valid JSON. Is set to [ADMINS setting](https://docs.djangoproject.com/en/3.1/ref/settings/#admins) of Django. Defaults to an empty list. |
| DJANGO_SECRET_KEY   | oTg2aWkM...                                       | Can be used to specify the [SECRET_KEY](https://docs.djangoproject.com/en/3.1/ref/settings/#std:setting-SECRET_KEY) setting of Django. Defaults to a random sequence of 64 chars generated on container startup. Note that changing the secret key will invalidate all cookies and thus force all user to login again. |
| FQ_HOSTNAME         | bemcom.domain.com                                 | The fully qualified hostname the API service should be hosted on. Is added to the [ALLOWED_HOSTS](https://docs.djangoproject.com/en/3.1/ref/settings/#allowed-hosts) setting of Django. Defaults to `localhost`, which means that API can only be accessed from the local machine. |
| SSL_CERT_PEM        | -----BEGIN CERTIFICATE-----<br/>MIIFCTCCAvG...    | The certificate to use for HTTPS. Will generate a self signed certificate if SSL_CERT_PEM or SSL_KEY_PEM are empty. The self signed certificate will make HTTPS work, but browsers will issue a warning. |
| SSL_KEY_PEM         | -----BEGIN PRIVATE KEY-----<br/>MIIJQgIBADANBg... | Similar to SSL_CERT_PEM but should hold the private key of the certificate. |
| DATABASE_SETTING    | see [Database Setup](#database-setup).            | Defines the default database for Django, see [Database Setup](#database-setup) for details. Defaults to SQLite with data stored in file source/db.sqlite3 . |
| N_CMI_WRITE_THREADS | 1                                                 | The number of parallel threads the api_main/connector_mqtt_integration.py script uses to push incomming MQTT messages into the Database. This must be an integer. Defaults to 1 as SQLite DBs don't support parallel read or write operations. For PostgreSQL DBs Values like 32 or above give a significant increase in write throughput. |


##### Volumes

None for most scenarios. Eventually a volume may be used to persist the SQLite database file. See below.



### Database Setup

You should be able to use any database [supported by Django](https://docs.djangoproject.com/en/3.1/ref/settings/#engine). Only PostgreSQL and SQLite have been tested so far.

##### SQLite

SQLite database are not recommended for production use. No setup is required for just testing the container. If the SQLite file should be persisted beyond the container life it is necessary to carry out the following steps:

* ```bash
  # Create an empty file so docker has something to mount
  touch /source/db.sqlite3
  ```

* Add the following line to the docker-compose file:

  ```
          volumes:
              - ./source/db.sqlite3:/source/db.sqlite3
  ```

##### Other Databases

For any database [supported by Django](https://docs.djangoproject.com/en/3.1/ref/settings/#engine) you need to set up the database yourself and provide an appropriate setting as JSON string on the DATABASE_SETTING environment variable. For example a valid JSON string for PostgreSQL configuration could look like this:

```json
{
    "ENGINE": "django.db.backends.postgresql",
    "NAME": "mydatabase",
    "USER": "mydatabaseuser",
    "PASSWORD": "mypassword",
    "HOST": "127.0.0.1",
    "PORT": "5432"
}
```

Note: that the API service uses only one database, and these settings are used as the default database. See [here](https://docs.djangoproject.com/en/3.1/ref/settings/#databases) for more details.

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



### TODO

* [ ] Alerting (E-Mail / Alertmanager) if operation goes wrong.
* [ ] Document return objects and codes for errors of REST interface.
* [ ] Add functionality to align timestamps while retrieving data from REST interface.
* [ ] Add functionality to disable controllers and the history DB to support new users.
* [ ] Add Websocket Push Interface.
* [ ] Fix adding Controller Admin Pages, there seems to be while defining controlled_datapoints.
* [ ] Extend documentation:
  * [ ] REST and UI Endpoints
  * [ ] How to set certs, e.g. with:`MODE=PROD SSL_KEY_PEM=$(cat key.pem) SSL_CERT_PEM=$(cat cert.pem) docker-compose up --build`
  * [ ] Security issues are monitored and new versions of this API are provided asap if a security issue in one of the components becomes known.



### Development Checklist

Follow the following steps while contributing to the connector:

* Create a `.env` file with suitable configuration for your local setup. It is usually a good idea to set the `DEBUG=TRUE` and `LOGLEVEL=DEBUG` for developing.

* If you have no Database set up yet, follow the steps of [Database Setup](#database-setup) above.

* For local development (the code is executed in a python environment on the machine):

  * Install dependencies with:

    ```bash
    pip install -r ./source/requirements.txt
    ```

  * Start the development server if needed with: 
    
    ```bash
    # --noreload prevents duplicate entries in DB.
    source/api/manage.py runserver --noreload
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

  

* Update the image name and tag in  [./build_docker_image.sh](./build_docker_image.sh) and [source/api/api_main/settings.py](source/api/api_main/settings.py) and execute the shell script to build an updated image.

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
| 0.3.0 | Datapoint Value and Available Datapoint messages and a can now contain any JSON data type as value. |
