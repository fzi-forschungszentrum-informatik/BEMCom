This folder holds the source code of the django api service.

# Run the API

<span style="color:red;font-weight:bold">TODO: Add documentation.</span>

# Run tests

within `django_code` folder run:

```
pytest
```



# Folder structure

The code is organized in these four modules

### general_configuration

Contains server configuration and settings of the service.

### main

Contains all relevant code to communicate with the connectors and the message broker and the corresponding DB models for Connectors and Datapoints.

### admin_ui

Contains the source code of the admin user interface that allows admins to manage and configure connectors, but also the REST API. 

### rest_api

Contains the source code for the REST API, that allows external access to the datapoints.