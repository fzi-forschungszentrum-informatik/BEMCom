# aquametro AMBUS Net Connector
This connector allows linking metering devices connected to [aquametro's AMBUS Net](https://aquametro.com/product/ambus-net/) device.




### Supported Gateways

| Manufacturer | Model     | Tested?/Remarks?                                             |
| ------------ | --------- | ------------------------------------------------------------ |
| aquametro    | AMBUS Net | Tested. The device should in theory be able to communicate with any SOAP client. However the SOAP configuration of our test device was slightly broken, which required some tweaking of the requests. This is incorporated in the connector. |



### Supported Devices

The connector should be able to process sensor datapoints of any meter that is supported by the AMBUS Net device. 

| Manufacturer | Model                                             | Tested?/Remarks?                                |
| ------------ | ------------------------------------------------- | ----------------------------------------------- |
| aquametro    | CALEC ST computation unit                         | Tested.                                         |
| aquametro    | AMFLO SONIC UFA-113 ultrasonic volume flow sensor | Tested in combination with the CALEC ST device. |



### Configuration

##### Ports

| Port                    | Usage/Remarks                                                |
| ----------------------- | ------------------------------------------------------------ |
| 1880                    | Node-RED development user interface.                         |

##### Environment Variables

| Enironment Variable    | Example  Value      | Usage/Remarks                                                |
| ---------------------- | ------------------- | ------------------------------------------------------------ |
| AMBUSNETWS_SOAP_URL  | http://127.0.0.1/AmbusNetWS/Service1.asmx | The Soap URL of the Ambus Net device.                        |
| METER_IDS            | [1, 2]                                    | The ids of the meters connected to the Ambus Net device that should be read out. |
| POLL_SECONDS         | 30                                        | Configures how often the meters should be polled.            |
| MAX_POLLS_PER_PERIOD | 15                                        | Configure rate limit, that is the delay between polling one and the next meter to prevent something DDOS like. This is the maximum number of requests per POLL_TIME that are sent to Ambus Net, which yields to POLL_SECONDS / MAX_POLLS_PER_PERIOD delay between two requests to Ambus Net. MAX_POLLS_PER_PERIOD should be significantly larger then number of entries in METER_IDS. |

##### Volumes

None.



### Development Checklist

Follow the following steps while contributing to the connector:

* Create a `.env` file with suitable configuration for your local setup.
* Optional: Update the image of the node-red-connector-template by editing [source/Dockerfile](source/Dockerfile) 
* Start the development instance with  `docker-compose up -d`
* Edit the flows, ensure everything works as expected.
* Export the changed flows and update/create the files in [./source/flows/](./source/flows/). The filenames should be the flows ids.
* Update the image tag in  [./build_docker_image.sh](./build_docker_image.sh) and execute the shell script to build an updated image. 
* Run the new image and check once more everything works as expected.
* Document your changes and new tag by appending the list below.
* git add, commit and push.



### Changelog

| Tag   | Changes                            |
| ----- | ---------------------------------- |
| 0.1.0 | Initial version.                   |
| 0.1.1 | Minor bug fix.                     |
| 0.2.0 | Update to connector template 0.3.0 |