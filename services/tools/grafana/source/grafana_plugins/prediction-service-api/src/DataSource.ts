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
  url: string;

  constructor(instanceSettings: DataSourceInstanceSettings<MyDataSourceOptions>) {
    super(instanceSettings);
    this.url = instanceSettings.url || '';
  }

  translateInterval(interval: string) {
    // translate the grafana typical notation of the interval ('1s'. '2h', ...)
    // to time-bucket like notation ('1 days', '30 seconds')
    const value = parseInt(interval.match(/\d/g)?.join('') || '');
    const type = interval.match(/\D/g)?.join('') || '';

    let newType = '';
    switch (type) {
      case 'ms':
        newType = 'milliseconds';
        break;
      case 's':
        newType = 'seconds';
        break;
      case 'm':
        newType = 'minutes';
        break;
      case 'h':
        newType = 'hours';
        break;
      case 'd':
        newType = 'days';
        break;
    }

    return value.toString() + ' ' + newType;
  }

  translateOffset(offset: string) {
    // translate the grafana typical notation of the interval ('1s'. '2h', ...)
    // to time-bucket like notation ('1 days', '30 seconds')
    const offsetParts = offset.split(' ');
    if (offsetParts.length != 2) {
      return '';
    }
    const value = parseFloat(offsetParts[0]);
    const type = offsetParts[1];

    let newType = '';
    switch (true) {
      case ['ms', 'milliseconds', 'milli'].indexOf(type) >= 0:
        newType = 'milliseconds';
        break;
      case ['s', 'sec', 'secs', 'seconds', 'second'].indexOf(type) >= 0:
        newType = 'seconds';
        break;
      case ['m', 'min', 'mins', 'minute', 'minutes'].indexOf(type) >= 0:
        newType = 'minutes';
        break;
      case ['h', 'hour', 'hours'].indexOf(type) >= 0:
        newType = 'hours';
        break;
      case ['d', 'day', 'days'].indexOf(type) >= 0:
        newType = 'days';
        break;
      case ['w', 'week', 'weeks'].indexOf(type) >= 0:
        newType = 'weeks';
        break;
      case ['M', 'month', 'months'].indexOf(type) >= 0:
        newType = 'months';
        break;
      case ['y', 'year', 'years'].indexOf(type) >= 0:
        newType = 'years';
        break;
    }

    return value.toString() + ' ' + newType;
  }

  async doRequest(query: { [k: string]: any }) {
    // type: MyQuery
    // build url
    const urlReq = this.url + '/request/';
    // get params from user input and parse to object
    const params: Object = JSON.parse(query.requestParamsJson);
    var resultReq;

    try {
      resultReq = await getBackendSrv().datasourceRequest({
        method: 'POST',
        url: urlReq,
        data: params,
        // headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      });
    } catch (error) {
      console.log('Error: ', error.status, ' ', error.statusText);
      return false;
    }

    // extract requestID
    if (resultReq.status != 201) {
      return false;
    }
    const requestID = resultReq.data.request_ID;
    const urlRes = this.url + '/request/' + requestID + '/result/';
    var resultRes;

    try {
      resultRes = await getBackendSrv().datasourceRequest({
        method: 'GET',
        url: urlRes,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      });
    } catch (error) {
      console.log('Error: ', error.status, ' ', error.statusText);
      return false;
    }

    return resultRes;
  }

  async query(options: DataQueryRequest<MyQuery>): Promise<DataQueryResponse> {
    const { range } = options;
    const from = range!.from.valueOf();
    const to = range!.to.valueOf();

    let targets = options.targets;
    targets.forEach((target) => {
      target.from = from;
      target.to = to;
    });

    const promises = targets.map((target) =>
      this.doRequest(target).then((response) => {
        if (!response || response.data === undefined || response.data.length === 0) {
          return [];
        }
        // time series like data.
        var frame = new MutableDataFrame({
          refId: target.refId,
          name: 'timeseries',
          fields: [{ name: 'time', type: FieldType.time }],
        });

        // parse returned data
        // #######################
        var data = response.data;
        // if name settings are provided, and filter is switsched on, only parse the provided fields
        const nameSettings = JSON.parse(target.nameSettingsJson || '{}');
        const filterByNames = target.filterByNames;

        if (Object.entries(nameSettings).length > 0 && filterByNames) {
          // add specified column names
          for (const key of Object.keys(nameSettings)) {
            frame.addField({ name: nameSettings[key], type: FieldType.number });
          }

          // build and add rows
          data[Object.keys(data)[0]].forEach((e: any, i: any) => {
            let row = [e['timestamp']];

            for (const key of Object.keys(nameSettings)) {
              row.push(data[key][i]['value']);
            }
            frame.appendRow(row);
          });
        } else {
          // add all column names
          for (const key of Object.keys(data)) {
            if (Object.keys(nameSettings).indexOf(key) >= 0) {
              frame.addField({ name: nameSettings[key], type: FieldType.number });
            } else {
              frame.addField({ name: key, type: FieldType.number });
            }
          }

          // build and add rows
          data[Object.keys(data)[0]].forEach((e: any, i: any) => {
            let row = [e['timestamp']];

            for (const key of Object.keys(data)) {
              row.push(data[key][i]['value']);
            }
            frame.appendRow(row);
          });
        }
        // #######################

        return frame;
      })
    );

    return Promise.all(promises).then((data) => ({ data }));
  }

  async testDatasource() {
    if (endsWith(this.url, '/')) {
      this.url = this.url.slice(0, -1);
    }

    var valid_GET_response = false;
    var valid_POST_response = false;
    var message = 'error';

    try {
      await getBackendSrv().datasourceRequest({
        // const resultGET =
        method: 'GET',
        url: this.url + '/request/',
        // params: { format: 'json' },
      });

      // should not be executed bc an error with status 405 is expected: GET should not be allowed
      valid_GET_response = false;
      message = 'Datasource did not respond properly';
    } catch (err) {
      if (err.status === 405) {
        valid_GET_response = true;
        message = 'success';
      } else if (err.status === 502) {
        valid_GET_response = false;
        message =
          err.status.toString() +
          ' - Bad Gateway. Maybe the url is wrong/ https is required/ a self signed certificate is used.';
      } else if (err.status === 400) {
        valid_GET_response = false;
        message = err.status.toString() + ' - Bad Reqeust';
        if (err.data.response === 'Authentication to data source failed') {
          message = message + '. Authentication to data source failed.';
        }
      } else {
        valid_GET_response = false;
        message = 'Unknown error ' + err.status.toString();
      }
    }

    // early abort test, if GET test already failed
    if (!valid_GET_response) {
      return {
        status: 'error',
        message: message,
      };
    }

    try {
      await getBackendSrv().datasourceRequest({
        //const resultPOST =
        method: 'POST',
        url: this.url + '/request/',
        // params: { format: 'json' },
      });

      // should not be executed bc an error with status 422 is expected: POST needs params
      valid_POST_response = false;
      message = 'Datasource did not respond properly';
    } catch (err) {
      if (err.status === 422) {
        valid_POST_response = true;
        message = 'success';
      } else if (err.status === 502) {
        valid_POST_response = false;
        message =
          err.status.toString() +
          ' - Bad Gateway. Maybe the url is wrong/ https is required/ a self signed certificate is used.';
      } else if (err.status === 400) {
        valid_POST_response = false;
        message = err.status.toString() + ' - Bad Reqeust';
        if (err.data.response === 'Authentication to data source failed') {
          message = message + '. Authentication to data source failed.';
        }
      } else {
        valid_POST_response = false;
        message = 'Unknown error ' + err.status.toString();
      }
    }

    return {
      status: valid_GET_response && valid_POST_response ? 'success' : 'error',
      message: message,
    };
  }
}
