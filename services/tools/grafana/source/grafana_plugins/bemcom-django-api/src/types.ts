import { DataQuery, DataSourceJsonData } from '@grafana/data';

export interface MyQuery extends DataQuery {
  getMeta: boolean;

  entries: MyQueryEntry[];
  // datapoints: new Array({ label: '', value: 0, description: '' }),
  // datatypes: new Array({ label: 'value', value: 0, description: 'timeseries of values' }),
  // displayNames: new Array(''),
  // scalingFactors: new Array(1),

  nQueries: number;
  from?: number;
  to?: number;
}

// defaults:
export const defaultQuery: Partial<MyQuery> = {
  getMeta: false,
  nQueries: 1,
  entries: new Array({
    id: 0,
    datapoint: { label: '', value: 0, description: '' },
    datatype: { label: 'value', value: 0, description: 'timeseries of values' },
    displayName: '',
    scalingFactor: 1,
  }),
};

export const defaultQueryEntry: MyQueryEntry = {
  id: NaN,
  datapoint: { label: '', value: 0, description: '' },
  datatype: { label: 'value', value: 0, description: 'timeseries of values' },
  displayName: '',
  scalingFactor: 1,
};

/**
 * These are options configured for each DataSource instance
 */
export interface MyDataSourceOptions extends DataSourceJsonData {
  useBasicAuth?: boolean;
  basicAuthUser?: string;
  tlsSkipVerify?: boolean;

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

export interface MyQueryEntry {
  id: number;
  datapoint: MyDatapoint;
  datatype: MyDatatype;
  displayName: string;
  scalingFactor: number;
}
