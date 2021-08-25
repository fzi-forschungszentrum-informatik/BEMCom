import React, { ChangeEvent, PureComponent } from 'react';
import { LegacyForms } from '@grafana/ui';
import { DataSourcePluginOptionsEditorProps } from '@grafana/data';
import { MyDataSourceOptions, MySecureJsonData } from './types';

const { FormField, SecretFormField } = LegacyForms;

import FormControlLabel from '@material-ui/core/FormControlLabel';
import { Checkbox, Switch } from '@material-ui/core';

interface Props extends DataSourcePluginOptionsEditorProps<MyDataSourceOptions> {}

interface State {}

export class ConfigEditor extends PureComponent<Props, State> {
  // constructor(props) {
  //   super(props);
  //   // this.props.options.basicAuth = false;
  // }

  onUriChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { onOptionsChange, options } = this.props;
    const url = event.target.value;
    onOptionsChange({ ...options, url });
  };

  // onLimitChange = (event: ChangeEvent<HTMLInputElement>) => {
  //   const { onOptionsChange, options } = this.props;
  //   const queryLimit = parseInt(event.target.value);
  //   onOptionsChange({
  //     ...options,
  //     jsonData: {
  //       ...options.jsonData,
  //       queryLimit,
  //     },
  //   });
  // };

  onBasicAuthChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { onOptionsChange, options } = this.props;
    const basicAuth = !(event.target.value === 'true');
    onOptionsChange({ ...options, basicAuth });
  };

  ontlsSkipVerifyChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { onOptionsChange, options } = this.props;
    const tlsSkipVerify = !(event.target.value === 'true');
    onOptionsChange({
      ...options,
      jsonData: {
        ...options.jsonData,
        tlsSkipVerify,
      },
    });
  };

  onUserChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { onOptionsChange, options } = this.props;
    const basicAuthUser = event.target.value;
    onOptionsChange({
      ...options,
      basicAuthUser,
      // jsonData: {
      //   user: event.target.value,
      // },
    });
  };

  // Secure field (only sent to the backend)
  onPasswordChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { onOptionsChange, options } = this.props;
    onOptionsChange({
      ...options,
      secureJsonData: {
        basicAuthPassword: event.target.value,
      },
    });
  };

  onResetPassword = () => {
    const { onOptionsChange, options } = this.props;
    onOptionsChange({
      ...options,
      secureJsonFields: { ...options.secureJsonFields, basicAuthPassword: false },
      secureJsonData: { ...options.secureJsonData, basicAuthPassword: '' },
    });
  };

  render() {
    // console.log('RENDER Config Editor - props: ', this.props);
    const { options } = this.props;
    const { secureJsonFields } = options;

    const jsonData = options.jsonData;
    const secureJsonData = (options.secureJsonData || {}) as MySecureJsonData;

    return (
      <div className="gf-form-group">
        <div className="gf-form-group">
          {/* URL */}
          <div className="gf-form">
            <FormField
              label="url"
              labelWidth={10}
              inputWidth={20}
              onChange={this.onUriChange}
              value={options.url || ''}
              placeholder="datasource 'http://example.com:8888/api'"
              tooltip="url to root of API"
            />
          </div>

          {/* Limit */}
          {/* <div className="gf-form">
            <FormField
              label="query limit"
              labelWidth={10}
              inputWidth={20}
              onChange={this.onLimitChange}
              value={jsonData.queryLimit || ''}
              placeholder="max number of requested entries per query"
              tooltip="Set a limit on the number of entries requested per query to prevent an exhausting query to crush the backend. Similar to the SQL LIMIT instruction."
            />
          </div> */}
        </div>

        {/* Use basicAuth */}
        <div className="gf-form-group">
          <div className="gf-form">
            <FormControlLabel
              control={
                <Switch
                  checked={options.basicAuth}
                  value={options.basicAuth}
                  onChange={this.onBasicAuthChange}
                  name="useBasicAtuh"
                  color="primary"
                  size="small"
                />
              }
              className="m-1"
              label="use basic authentication"
            />
          </div>

          {/* basicAuth user */}
          <div className="gf-form-group">
            <div className="gf-form">
              <FormField
                label="user"
                placeholder="username"
                tooltip="basicAuth user"
                labelWidth={10}
                inputWidth={20}
                onChange={this.onUserChange}
                value={options.basicAuthUser || ''}
                disabled={!options.basicAuth}
              />
            </div>

            {/* basicAuth password */}
            <div className="gf-form">
              <SecretFormField
                label="password"
                placeholder="password"
                tooltip="basicAuth password"
                labelWidth={10}
                inputWidth={20}
                isConfigured={(secureJsonFields && secureJsonFields.basicAuthPassword) as boolean}
                onChange={this.onPasswordChange}
                onReset={this.onResetPassword}
                value={secureJsonData.basicAuthPassword || ''}
                disabled={!options.basicAuth}
              />
            </div>
          </div>
        </div>

        {/* Skip TLS Verification */}
        <div className="gf-form-group">
          <div className="gf-form">
            <FormControlLabel
              control={
                <Checkbox
                  checked={jsonData.tlsSkipVerify}
                  value={jsonData.tlsSkipVerify}
                  onChange={this.ontlsSkipVerifyChange}
                  name="skip tls verify"
                  color="primary"
                  size="small"
                />
              }
              className="m-1"
              label="skip TLS verification (insecure! Use for self signed certificates - for now)"
            />
          </div>
        </div>
      </div>
    );
  }
}
