import { DataQuery, DataSourceJsonData } from '@grafana/data';

export interface MyQuery extends DataQuery {
  requestParamsJson: string;
  from?: number;
  to?: number;

  nameSettingsJson: string;
  filterByNames: boolean;
}

// defaults:
export const defaultQuery: Partial<MyQuery> = {
  nameSettingsJson: '',
  filterByNames: false,
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
