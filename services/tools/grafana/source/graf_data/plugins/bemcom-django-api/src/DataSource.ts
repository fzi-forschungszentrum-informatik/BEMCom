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

  async doRequest(query: MyQuery) {
    // console.log('inside doRequests. Query is:', query);
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
    // console.log('Inside query - ');
    const { range } = options;
    const from = range!.from.valueOf();
    const to = range!.to.valueOf();
    options.targets.forEach(target => {
      target.from = from;
      target.to = to;
    });

    const promises = options.targets.map(target =>
      this.doRequest(target).then(response => {
        if (!response || response.data == undefined || response.data.length == 0) {
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

          switch (target.datatype?.label) {
            case 'value':
              frame.name = 'value';
              frame.addField({ name: target.datapoint?.label + '_value' || 'value', type: FieldType.number });

              // sort response.data by timestamps
              response.data = response.data.sort((first: any, second: any) => {
                return first.timestamp > second.timestamp ? 1 : -1;
              });

              response.data.forEach((point: any) => {
                frame.appendRow([point.timestamp, point.value]);
              });
              break;
            case 'schedule':
              frame.name = 'schedule';
              frame.addField({ name: target.datapoint?.label + '_schedule' || 'schedule', type: FieldType.number });

              // sort response.data by timestamps
              response.data = response.data.sort((first: any, second: any) => {
                return first.timestamp > second.timestamp ? 1 : -1;
              });

              let latest_schedule = response.data[response.data.length - 1];
              // response.data.forEach((schedule: any) => {
              //   if (schedule.timestamp > latest_schedule.timestamp) {
              //     latest_schedule = schedule;
              //   }
              // });

              latest_schedule.schedule.forEach((interval: any) => {
                // set frame content
                // check if from or to is null
                if (interval.from_timestamp == null) {
                  frame.appendRow([interval.to_timestamp - 1, interval.value]);
                } else if (interval.to_timestamp == null) {
                  frame.appendRow([interval.from_timestamp, interval.value]);
                } else {
                  frame.appendRow([interval.from_timestamp, interval.value]);
                  frame.appendRow([interval.to_timestamp - 1, interval.value]);
                }
              });

              break;
            case 'setpoint':
              // sort response.data by timestamps
              response.data = response.data.sort((first: any, second: any) => {
                return first.timestamp > second.timestamp ? 1 : -1;
              });

              let latest_setpoint = response.data[response.data.length - 1];
              // response.data.forEach((setpoint: any) => {
              //   if (setpoint.timestamp > latest_setpoint.timestamp) {
              //     latest_setpoint = setpoint;
              //   }
              // });

              frame.name = 'setpoint';
              frame.addField({
                name: target.datapoint?.label + '_lower_bound' || 'lower_bound',
                type: FieldType.number,
              });
              frame.addField({
                name: target.datapoint?.label + '_upper_bound' || 'upper_bound',
                type: FieldType.number,
              });
              frame.addField({
                name: target.datapoint?.label + '_preferred_value' || 'preferred_value',
                type: FieldType.number,
              });

              latest_setpoint.setpoint.forEach((interval: any) => {
                let acceptable_values = interval.acceptable_values.map((x: string) => Number(x));
                let preferred_value = Number(interval.preferred_value);

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
          console.log('frame.fields:');
          console.log(frame.fields);
          return frame;
        }
      })
    );
    return Promise.all(promises).then(data => ({ data }));
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
      if (err.status == 502) {
        return {
          status: 'error',
          message:
            err.status.toString() +
            ' - Bad Gateway. Maybe the url is wrong/ https is required/ a self signed certificate is used.',
        };
      } else if (err.status == 400) {
        let message = err.status.toString() + ' - Bad Reqeust';

        if (err.data.response == 'Authentication to data source failed') {
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
