// import defaults from 'lodash/defaults';
import { getBackendSrv } from '@grafana/runtime';

import {
  DataQueryRequest,
  DataQueryResponse,
  DataSourceApi,
  DataSourceInstanceSettings,
  MutableDataFrame,
  FieldType,
} from '@grafana/data';

import { MyQuery, MyDataSourceOptions } from './types';
import { endsWith } from 'lodash';

export class DataSource extends DataSourceApi<MyQuery, MyDataSourceOptions> {
  // settings: DataSourceInstanceSettings;
  url: string;

  constructor(instanceSettings: DataSourceInstanceSettings<MyDataSourceOptions>) {
    super(instanceSettings);
    // this.settings = instanceSettings;
    this.url = instanceSettings.url || '';
  }

  async doRequest(query: { [k: string]: any }) {
    // type: MyQuery
    // build url
    let url = '';
    if (query.getMeta) {
      // get meta data ignore other query parameters
      url = this.url + '/datapoint/';
    } else {
      const deviceId = query.datapoint ? query.datapoint.value : 1;
      const type = query.datatype
        ? query.datatype.label.includes('setpoint')
          ? 'setpoint'
          : query.datatype.label
        : 'value';
      url = this.url + '/datapoint/' + deviceId + '/' + type + '/';
    }

    // build query parameters
    const params = {
      timestamp__gte: query.from,
      timestamp__lte: query.to,
    };

    try {
      const result = await getBackendSrv().datasourceRequest({
        method: 'GET',
        url: url,
        params: params,
        // headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      });

      return result;
    } catch (error) {
      console.log('Error: ', error.status, ' ', error.statusText);
      return false;
    }
  }

  async query(options: DataQueryRequest<MyQuery>): Promise<DataQueryResponse> {
    const { range } = options;
    const from = range!.from.valueOf();
    const to = range!.to.valueOf();

    // for queries defined by Grafana UI:
    // options.targets.forEach((mainQuery) => {});

    const mainQuery: MyQuery | undefined = options.targets.pop();

    let targets: { [k: string]: any }[] = [];

    // handle getMeta
    if (mainQuery?.getMeta) {
      let newTarget: { [k: string]: any } = {};
      newTarget.getMeta = mainQuery?.getMeta;

      newTarget.refId = mainQuery?.refId || '';
      newTarget.datasource = mainQuery?.datasource || '';
      newTarget.from = from || '';
      newTarget.to = to || '';

      targets.push(newTarget);
    } else {
      // handle normal query if getMeta is false

      mainQuery?.entries.forEach((entry) => {
        let newTarget: { [k: string]: any } = {};
        newTarget.datapoint = entry.datapoint;
        newTarget.datatype = entry.datatype;
        newTarget.displayName = entry.displayName;
        newTarget.scalingFactor = entry.scalingFactor;

        newTarget.refId = mainQuery?.refId || '';
        newTarget.datasource = mainQuery?.datasource || '';
        newTarget.from = from || '';
        newTarget.to = to || '';
        targets.push(newTarget);
      });
    }

    // const promises = options.targets.map((target) =>
    const promises = targets.map((target) =>
      this.doRequest(target).then((response) => {
        if (!response || response.data === undefined || response.data.length === 0) {
          return [];
        }
        if (target.getMeta) {
          // table like data.
          return response.data;
        } else {
          // time series like data.
          var frame = new MutableDataFrame({
            refId: target.refId,
            name: 'timeseries',
            fields: [{ name: 'time', type: FieldType.time }],
          });

          // use displayName and scalingFactor
          const displayName = target.displayName || target.datapoint?.label;
          const scalingFactor = target.scalingFactor || 1;

          switch (target.datatype?.label) {
            case 'value':
              frame.name = 'value';
              frame.addField({ name: displayName || 'value', type: FieldType.number });

              // sort response.data by timestamps
              response.data = response.data.sort((first: any, second: any) => {
                return first.timestamp > second.timestamp ? 1 : -1;
              });

              response.data.forEach((point: any) => {
                frame.appendRow([point.timestamp, point.value * scalingFactor]);
              });
              break;
            case 'schedule':
              frame.name = 'schedule';
              frame.addField({ name: displayName || 'schedule', type: FieldType.number });

              // sort response.data by timestamps
              response.data = response.data.sort((first: any, second: any) => {
                return first.timestamp > second.timestamp ? 1 : -1;
              });

              let latest_schedule = response.data[response.data.length - 1];

              latest_schedule.schedule.forEach((interval: any) => {
                // set frame content
                // check if from or to is null
                if (interval.from_timestamp == null) {
                  frame.appendRow([interval.to_timestamp - 1, interval.value * scalingFactor]);
                } else if (interval.to_timestamp == null) {
                  frame.appendRow([interval.from_timestamp, interval.value * scalingFactor]);
                } else {
                  frame.appendRow([interval.from_timestamp, interval.value * scalingFactor]);
                  frame.appendRow([interval.to_timestamp - 1, interval.value * scalingFactor]);
                }
              });

              break;
            case 'setpoint':
              // sort response.data by timestamps
              response.data = response.data.sort((first: any, second: any) => {
                return first.timestamp > second.timestamp ? 1 : -1;
              });

              let latest_setpoint = response.data[response.data.length - 1];

              frame.name = 'setpoint';
              frame.addField({
                name: displayName + '_low' || 'lower_bound',
                type: FieldType.number,
              });
              frame.addField({
                name: displayName + '_up' || 'upper_bound',
                type: FieldType.number,
              });
              frame.addField({
                name: displayName + '_pref' || 'preferred_value',
                type: FieldType.number,
              });

              latest_setpoint.setpoint.forEach((interval: any) => {
                let acceptable_values = interval.acceptable_values.map((x: string) => Number(x) * scalingFactor);
                let preferred_value = Number(interval.preferred_value) * scalingFactor;

                // check if from or to is null
                if (interval.from_timestamp == null) {
                  frame.appendRow([
                    interval.to_timestamp - 1,
                    Math.min(...acceptable_values),
                    Math.max(...acceptable_values),
                    preferred_value,
                  ]);
                } else if (interval.to_timestamp == null) {
                  frame.appendRow([
                    interval.from_timestamp,
                    Math.min(...acceptable_values),
                    Math.max(...acceptable_values),
                    preferred_value,
                  ]);
                } else {
                  frame.appendRow([
                    interval.from_timestamp,
                    Math.min(...acceptable_values),
                    Math.max(...acceptable_values),
                    preferred_value,
                  ]);
                  frame.appendRow([
                    interval.to_timestamp - 1,
                    Math.min(...acceptable_values),
                    Math.max(...acceptable_values),
                    preferred_value,
                  ]);
                }
              });
              break;
          }
          return frame;
        }
      })
    );

    return Promise.all(promises).then((data) => ({ data }));
  }

  async testDatasource() {
    if (endsWith(this.url, '/')) {
      this.url = this.url.slice(0, -1);
    }

    try {
      const result = await getBackendSrv().datasourceRequest({
        method: 'GET',
        url: this.url + '/datapoint/',
        params: { format: 'json' },
      });

      if (result.status === 200) {
        return {
          status: 'success',
          message: 'Success',
        };
      } else {
        return {
          status: 'error',
          message: 'Datasource did not respond properly',
        };
      }
    } catch (err) {
      if (err.status === 502) {
        return {
          status: 'error',
          message:
            err.status.toString() +
            ' - Bad Gateway. Maybe the url is wrong/ https is required/ a self signed certificate is used.',
        };
      } else if (err.status === 400) {
        let message = err.status.toString() + ' - Bad Reqeust';

        if (err.data.response === 'Authentication to data source failed') {
          message = message + '. Authentication to data source failed.';
        }
        return {
          status: 'error',
          message: message,
        };
      } else {
        return {
          status: 'error',
          message: 'Unknown error ' + err.status.toString(),
        };
      }
    }
  }
}
