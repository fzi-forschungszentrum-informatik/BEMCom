# TODO
Remove FZI specific default values.

# Configuration / Environment Variables

| Environment Variable | Example Value                             | Explanation                                                  |
| -------------------- | ----------------------------------------- | ------------------------------------------------------------ |
| AMBUSNETWS_SOAP_URL  | http://127.0.0.1/AmbusNetWS/Service1.asmx | The Soap URL of the Ambus Net device.                        |
| METER_IDS            | [1, 2]                                    | The ids of the meters connected to the Ambus Net device that should be read out. |
| POLL_SECONDS         | 30                                        | Configures how often the meters should be polled.            |
| MAX_POLLS_PER_PERIOD | 15                                        | Configure rate limit, that is the delay between polling one and the next meter to prevent something DDOS like. This is the maximum number of requests per POLL_TIME that are sent to Ambus Net, which yields to POLL_SECONDS / MAX_POLLS_PER_PERIOD delay between two requests to Ambus Net. MAX_POLLS_PER_PERIOD should be significantly larger then number of entries in METER_IDS. |

