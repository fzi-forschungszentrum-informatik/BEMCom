import { DataQuery, DataSourceJsonData } from '@grafana/data';

export interface MyQuery extends DataQuery {
  getMeta: boolean;
  datapoint?: MyDatapoint;
  datatype?: MyDatatype;
  from?: number;
  to?: number;

  // queryText?: string;
  // constant: number;
}

export const defaultQuery: Partial<MyQuery> = {
  getMeta: false,
  datapoint: { label: '', value: 0, description: '' },
  datatype: { label: 'value', value: 0, description: 'timeseries of values' },

  // constant: 6.5,
};

/**
 * These are options configured for each DataSource instance
 */
export interface MyDataSourceOptions extends DataSourceJsonData {
  // host?: string;
  // path?: string;
}

/**
 * Value that is used in the backend, but never sent over HTTP to the frontend
 */
export interface MySecureJsonData {
  // apiKey?: string;
}

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
