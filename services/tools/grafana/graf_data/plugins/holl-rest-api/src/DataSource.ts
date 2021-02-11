// import defaults from 'lodash/defaults';
import { getBackendSrv } from '@grafana/runtime';

import {
  DataQueryRequest,
  DataQueryResponse,
  DataSourceApi,
  DataSourceInstanceSettings,
  MutableDataFrame,
  FieldType,
  // getColumnFromDimension,
} from '@grafana/data';

import { MyQuery, MyDataSourceOptions } from './types';

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
        url: url, // '/api/datasources/proxy/1/datapoint/', //http://localhost:3000/api/datasources/proxy/1/datapoint/
        params: params,
        // headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      });

      return result;
    } catch (error) {
      console.log('Error when requesting Datasource: ', error);
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
          const frame = new MutableDataFrame({
            refId: target.refId,
            fields: [
              { name: 'Time', type: FieldType.time },
              { name: 'Value', type: FieldType.number },
            ],
          });

          switch (target.datatype?.label) {
            case 'value':
              response.data.forEach((point: any) => {
                frame.appendRow([point.timestamp, point.value]);
              });
              break;
            case 'schedule':
              let latest_schedule = response.data[response.data.length - 1];
              response.data.forEach((schedule: any) => {
                if (schedule.timestamp > latest_schedule.timestamp) {
                  latest_schedule = schedule;
                }
              });
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
            case 'setpoint lower':
              let latest_setpoint = response.data[response.data.length - 1];
              response.data.forEach((setpoint: any) => {
                if (setpoint.timestamp > latest_setpoint.timestamp) {
                  latest_setpoint = setpoint;
                }
              });

              latest_setpoint.setpoint.forEach((interval: any) => {
                let number_interval = interval.acceptable_values.map((x: string) => Number(x));
                // set frame content
                // check if from or to is null
                if (interval.from_timestamp == null) {
                  frame.appendRow([interval.to_timestamp - 1, Math.min(...number_interval)]);
                } else if (interval.to_timestamp == null) {
                  frame.appendRow([interval.from_timestamp, Math.min(...number_interval)]);
                } else {
                  frame.appendRow([interval.from_timestamp, Math.min(...number_interval)]);
                  frame.appendRow([interval.to_timestamp - 1, Math.min(...number_interval)]);
                }
              });
              break;
            case 'setpoint upper':
              let latest_setpoint_up = response.data[response.data.length - 1];
              response.data.forEach((setpoint: any) => {
                if (setpoint.timestamp > latest_setpoint_up.timestamp) {
                  latest_setpoint_up = setpoint;
                }
              });

              latest_setpoint_up.setpoint.forEach((interval: any) => {
                let number_interval = interval.acceptable_values.map((x: string) => Number(x));
                // set frame content
                // check if from or to is null
                if (interval.from_timestamp == null) {
                  frame.appendRow([interval.to_timestamp - 1, Math.max(...number_interval)]);
                } else if (interval.to_timestamp == null) {
                  frame.appendRow([interval.from_timestamp, Math.max(...number_interval)]);
                } else {
                  frame.appendRow([interval.from_timestamp, Math.max(...number_interval)]);
                  frame.appendRow([interval.to_timestamp - 1, Math.max(...number_interval)]);
                }
              });
              break;
          }

          return frame;
        }
      })
    );
    return Promise.all(promises).then(data => ({ data }));
  }

  async testDatasource() {
    // TODO Implement a proper health check for the api root

    const result = await getBackendSrv().datasourceRequest({
      method: 'GET',
      url: this.url + '/',
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
  }
}
