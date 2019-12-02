This library allows the efficient creation of applications that can be used to connect a wide range of devices and data sources (e.g. webservices). All communication is bundled through a central API. This library follows a service oriented design in which functionality is encapsulated in services (i.e. docker containers).

# Creating Applications

The creation of applications from existing services requires only configuration and executing of the application_build tool. Regarding the creation of new services it is possible to use templates to reduce the implementation effort. See the [documentation]() for more details.

# Application Concept

Each created application will consist of several services with different functionalities. The following shows the general dataflow in an application.

![service_concept](graphics/service_concept.png)

As already mentioned, the general purpose of the application is to connect **devices** (or other data sources) to a central interface. Devices are represented as **sensor and actuator** datapoints, whereby one datapoint represents one value. Devices may use any form of communication. If the communication is not Ethernet based, it is necessary to use **hardware gateways**, that are devices that translate the device specific communication to Ethernet. An example could be Bluetooth room sensor (the device) that has two datapoints, e.g. the measured values for humidity and temperature. In order connect the device to the application a Raspberry Pi could be used that forwards the measured values from Bluetooth to a TCP socket.

The following group of services are **connectors** which translate the gateway specific message format to the shared message format used by all services directly connected to the message broker. The message will then be sent to the **message broker** which connects the services with each other. As usual,  **databases**  allow storing  Finally the central user and administration interface (**API**) is the only interaction endpoint for users and administrators alike. Returning to our example, a connector would listen to the gatway's TCP socket and convert incoming messages to the defined message format and sends them via MQTT to the message broker. Users would finally access the measured values by accessing a web based user interface which would use API. 