# Grafana instance with holl specific REST API plugin

This monitoring service provides a grafana instance with a self-written datasource plugin to visualize data from the BEMcom REST API.

The REST API basically provides datapoints with three types of time series data:

- values - measured values of the datapoint
- set-points - a user input marking an interval of acceptable values as well as a preferred value for one or several time intervals
- schedules - the road map to be executed. A schedule could be inferred by an optimzation service given a set-point as input

Not all datapoints provide all types of data as a datapoint can be a sensor - thus having values but no schedules - as well as an actor - having also schedules and set-points.

See the BEMcom documentation (TODO: insert link) for more details.

Thus, the holl-rest-api datasource plugin for grafana can display these three types of time series quickly.

### On the holl-rest-api plugin

#### Data source configuration

The datasource is simply configured by providing a url to the APIs root. For example `http://example.fzi.de:8017/api`.

Authentication is not supported by the initial version 0.1.0.

#### Query configuration

A query can either display meta data on the API or timeseries data.

**Meta data** is toggled by a switch. The received table-like data gives information on all available datapoints.

**Timeseries data** can be of the above described data types. Simply choose the datapoint by its short name and the datatype.
The dropdown also features an autoselection when typing.

TODO: implement auto detection of available data types for the selected datapoint.

#### Development

The plugin is written in typescript and based on the [grafana plugin creator and tutorial](https://grafana.com/tutorials/build-a-data-source-plugin/).

You can...

- Install all needed modules for development from within the `holl-rest-api` folder with <br>
  `npm install`
- Make your changes to the source files under `./graf_data/plugins/holl-rest-api/src`
- Hot build the plugin to see changes in the browser on reload with `yarn dev --watch`
- Build the plugin for production with `yarn build`

### Configuration

##### Ports

| Port | Usage/Remarks           |
| ---- | ----------------------- |
| 3000 | Default Grafana Ui port |

##### Environment Variables

| Enironment Variable        | Example Value | Usage/Remarks              |
| -------------------------- | ------------- | -------------------------- |
| GF_SECURITY_ADMIN_USER     | admin         | The default admin user     |
| GF_SECURITY_ADMIN_PASSWORD | password      | The default admin password |

##### Volumes

| Path in Container                | Usage/Remarks                      |
| -------------------------------- | ---------------------------------- |
| /graf_data/plugins/holl-rest-api | Contains the holl-rest-api plugin. |

### Changelog

| Tag   | Changes         |
| ----- | --------------- |
| 0.1.0 | Initial version |
