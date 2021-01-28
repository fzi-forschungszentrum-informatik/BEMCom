# Grafana instance with holl specific REST API plugin

This monitoring service provides a grafana instance with a self-written datasource plugin to visualize data from the BEMcom REST API.

The REST API basically provides datapoints with three types of timeseries data:

- values - measured values of the datapoint
- set-points - a user input marking an interval of acceptable values as well as a preferred value for one or several time intervals
- schedules - the road map to be executed. A schedule could be inferred by an optimzation service given a set-point as input

Not all datapoints provide all types of data as a datapoint can be a sensor - thus having values but no schedules - as well as an actor - having schedules and set-points as well.

See the BEMcom documentation (TODO: insert link) for more details.

Thus, the holl-rest-api datasource plugin for grafana can display these three types of data quickly.

### On the holl-rest-api plugin

#### Data source configuration

The datasource is simply configured by providing a url to the APIs root. For example `http://example.fzi.de:8017/api`.

Authentication is not supported by the initial version 0.1.0.

#### Query configuration

A query can either display meta data on the API or timeseries data.

**Meta data** is toggled by a switch. The received table-like data gives information on all available datapoints.

**Timeseries data** can be of the above described data types. Simply choose the datapoint by its short name and the datatype.

TODO: implement autocompletion instead of dropdown for datapoint selection. <br>
TODO: implement auto detection of available data types for the selected datapoint.

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

| Tag   | Changes          |
| ----- | ---------------- |
| 0.1.0 | Initial version. |
