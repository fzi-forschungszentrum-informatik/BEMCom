# Writing own plugin

typescript

# Plugins and Problems:

- JSON API: -
- Simple JSON: Must adjust API to meet standards of the plugin (see blow)
- JSON: Based on Simple JSON, so the same problems

official plugins for json:
	https://grafana.com/grafana/plugins?search=json&type=datasource&utm_source=grafana_add_ds

Post that refers to another not officially found plugin:
	https://www.reddit.com/r/grafana/comments/iovc4n/rest_api_as_data_source/

## JSON API
url: https://grafana.com/grafana/plugins/marcusolsson-json-datasource/installation?src=grafana_add_ds&pg=plugins&plcmt=featured-undefined
install:
	grafana-cli plugins install marcusolsson-json-datasource

this plugin is especially good to display parts of a big json as it supports jsonpath to specifically query only a part of the json.
This could be the thing...


## Simple JSON

install simple JSON plugin (https://grafana.com/grafana/plugins/grafana-simple-json-datasource):

	grafana-cli plugins install grafana-simple-json-datasource

The API must provide the following endpoints:

/search -> delivers the names of the metrics available in graphana

/annotations -> returns annotations... ok?

/query -> delivers data according to req body. req body contains the metric as defined under the /search endpoint
	req.body contains: {...targets: [ { target: 'upper_50', refId: 'A', type: 'timeserie' } ], ...}
	where upper_50 is the metric queried.

