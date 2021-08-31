import { DataQuery, DataSourceJsonData } from '@grafana/data';

export interface MyQuery extends DataQuery {
  getMeta: boolean;

  datapoint: MyDatapoint;
  datatype: MyDatatype;
  displayName: string;
  scalingFactor: number;

  interval?: string;
  offset?: string;
  useIntervalAndOffset?: boolean;

  nQueries: number;
  from?: number;
  to?: number;
}

// defaults:
export const defaultQuery: Partial<MyQuery> = {
  getMeta: false,
  datapoint: { label: '', value: 0, description: '' },
  datatype: { label: 'value', value: 0, description: 'timeseries of values' },
  displayName: '',
  scalingFactor: 1,
  useIntervalAndOffset: true,
};

/**
 * These are options configured for each DataSource instance
 */
export interface MyDataSourceOptions extends DataSourceJsonData {
  useBasicAuth?: boolean;
  basicAuthUser?: string;
  tlsSkipVerify?: boolean;
  queryLimit?: number;

  user?: string;
}

// export const defaultDataSourceOptions: Partial<MyDataSourceOptions> = {
//   useBasicAuth: false,
// };

/**
 * Value that is used in the backend, but never sent over HTTP to the frontend
 */
export interface MySecureJsonData {
  basicAuthPassword?: string;
}

// custom data types
export interface MyDatapoint {
  label: string;
  value: number;
  description: string;
}

export interface MyDatatype {
  label: string;
  value: number;
  description: string;
}
