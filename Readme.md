This library allows the efficient creation of applications that can be used to connect a wide range of devices and data sources (e.g. webservices). All communication is bundled through a central API. This library follows a service oriented design in which functionality is encapsulated in services (i.e. docker containers).

# Documentation

Is provided [here](documentation/Readme.md). This library relies heavily on docker and docker-compose. You may wish to familiarize yourself with these tools before using this library. A good starting point are the getting started pages of [docker](https://docs.docker.com/get-started/) and [docker-compose](https://docs.docker.com/compose/gettingstarted/) respectively.

# Creating Applications

The creation of applications from existing services requires only configuration and executing of the application_build tool. Regarding the creation of new services it is possible to use templates to reduce the implementation effort. See the [documentation](./documentation/04_application_builder.md) for more details.

# Application Concept

Each created application will consist of several services with different functionalities. The following shows the general dataflow in an application.

![service_concept](documentation/graphics/service_concept.png)

As already mentioned, the general purpose of the application is to connect **devices** (or other data sources) to a central interface. Devices are represented as **sensor and actuator** datapoints, whereby one datapoint represents one value. Devices may use any form of communication. If the communication is not Ethernet based, it is necessary to use **hardware gateways**, that are devices that translate the device specific communication to Ethernet. An example could be Bluetooth room sensor (the device) that has two datapoints, e.g. the measured values for humidity and temperature. In order connect the device to the application a Raspberry Pi could be used that forwards the measured values from Bluetooth to a TCP socket.

The following group of services are **connectors** which translate the gateway specific message format to the shared message format used by all services directly connected to the message broker. The message will then be sent to the **message broker** which connects the services with each other. As usual,  **databases**  allow storing  Finally the central user and administration interface (**API**) is the only interaction endpoint for users and administrators alike. Returning to our example, a connector would listen to the gatway's TCP socket and convert incoming messages to the defined message format and sends them via MQTT to the message broker. Users would finally access the measured values by accessing a web based user interface which would use API. 

# Running Applications

Run `docker-compose up -d` in your application. Try it out on the [demo application](./applications/demo).

# Folder Structure

### [applications](./applications)

Is used by the [application builder](./documentation/application_builder.md) to place the files of a built application.

### [application_builder](./application_builder)

Contains the tool to build applications from services. See the [application builder documentation](./documentation/application_builder.md) for more details.

### [application_templates](./application_templates)

Place all configuration required for building your applications here, see the [application builder documentation](./documentation/application_builder.md) for more details.

### [documentation](./documentation)

Contains more detailed documentation. Check also the [table of contents](./documentation/Readme.md) of the documentation.

### [services](./services)

Contains ready-to-use services for use in your applications. 

### [service_templates](./service_templates)

Contains templates that can be used to efficiently create new services.

# Contributors

TBA

# License

MIT?