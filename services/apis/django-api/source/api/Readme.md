# Folder structure

The code is organized in these four modules

### api_main

Contains the core elements of the API service:

* The settings holding the configuration of the service incl. parsing from environment variables.
* Database models and migrations.
* The logic to communicate with other services over MQTT (lives in`mqtt_integration.py`) and the signals that trigger automatic MQTT message updates on configuration changes. 

### api_admin_ui

Contains the source code of the admin user interface that allows admins to manage and configure the BEMCom application. 

### api_rest_interface

Contains the code for the REST interface including the automatic generation of the OpenAPI schema.

### ems_utils

Contains generic base classes for the models in api_main and serializers and views for the REST interface. Also holds some generic utility functions. All the code here has it's home in the BEMCom repository but is intended to bootstrap (by copy&paste of the module) other Django based programs that interact with the API service.  