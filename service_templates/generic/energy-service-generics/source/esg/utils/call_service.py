import json
from time import sleep

import requests

endpoint = "https://iik-energy-services.fzi.de/dwd-icon-data-service/v1/"

auth = requests.auth.HTTPBasicAuth(
    "username", "password"
)

request_response = requests.post(
    endpoint + "request/",
    auth=auth,
    json={
        # forecast of temperature und global radiation ...
        "fields": ["t_2m", "aswdir_s"],
        # .. for the simulated building.
        "positions": {
            "KIT-CN-449": {
                "latitude": 49.09576212865937,
                "longitude": 8.432979764581106,
            }
        },
        # requests data from the latest forecast available at this time,
        # i.e. the current simulated time of feenv. This value must be
        # adapted for every simulation step.
        "available_at": "2021-09-01T09:15:00+00:00",
        # Request forecasts for the next 24 hours. These value must be
        # adapted for every simulation step too.
        "forecast_from": "2021-09-01T09:15:00+00:00",
        "forecast_to": "2021-09-02T09:14:00+00:00",
        # Request resolution of 15 minutes.
        "time_resolution": 15,
        # This is important to retrieve the correct values for global
        # radiation. See the API schema for details if you care.
        "postprocessing": True,
    },
)

if request_response.status_code != 201:
    raise RuntimeError("Error while creating request.")

# This is the internal id under which the request is processed by the service.
request_ID = request_response.json()["request_ID"]

# Check if the request is ready for retrieval. Wait no more then 5 minutes.
ready = False
for i in range(300):
    status_response = requests.get(
        endpoint + ("request/%s/status/" % request_ID), auth=auth,
    )

    if status_response.status_code != 200:
        raise RuntimeError("Error while fetching request status.")

    status = status_response.json()
    if status["status_text"] == "ready":
        ready = True
        break
    else:
        sleep(1)

if not ready:
    raise RuntimeError("Request Timed out.")

# Finally, now that the result is ready, retrieve the result.
result_response = requests.get(
    endpoint + ("request/%s/result/" % request_ID), auth=auth,
)

if result_response.status_code != 200:
    raise RuntimeError("Error while fetching request result.")

forecast_data = result_response.json()

print(
    "This is the data that should be forwarded to the optimization algorithm."
)
print(json.dumps(forecast_data["icon_data"]["KIT-CN-449"], indent=4))
