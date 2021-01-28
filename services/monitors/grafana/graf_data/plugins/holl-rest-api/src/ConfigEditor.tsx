import React, { ChangeEvent, PureComponent } from 'react';
import { LegacyForms } from '@grafana/ui';
import { DataSourcePluginOptionsEditorProps } from '@grafana/data';
import { MyDataSourceOptions } from './types'; // MySecureJsonData

const { FormField } = LegacyForms; //SecretFormField

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

  // onHostChange = (event: ChangeEvent<HTMLInputElement>) => {
  //   const { onOptionsChange, options } = this.props;
  //   const jsonData = {
  //     ...options.jsonData,
  //     host: event.target.value,
  //   };
  //   onOptionsChange({ ...options, jsonData });
  // };

  // onPathChange = (event: ChangeEvent<HTMLInputElement>) => {
  //   const { onOptionsChange, options } = this.props;
  //   const jsonData = {
  //     ...options.jsonData,
  //     path: event.target.value,
  //   };
  //   onOptionsChange({ ...options, jsonData });
  // };

  // // Secure field (only sent to the backend)
  // onAPIKeyChange = (event: ChangeEvent<HTMLInputElement>) => {
  //   const { onOptionsChange, options } = this.props;
  //   onOptionsChange({
  //     ...options,
  //     secureJsonData: {
  //       apiKey: event.target.value,
  //     },
  //   });
  // };

  // onResetAPIKey = () => {
  //   const { onOptionsChange, options } = this.props;
  //   onOptionsChange({
  //     ...options,
  //     secureJsonFields: {
  //       ...options.secureJsonFields,
  //       apiKey: false,
  //     },
  //     secureJsonData: {
  //       ...options.secureJsonData,
  //       apiKey: '',
  //     },
  //   });
  // };

  render() {
    console.log('RENDER Config Editr - options: ', this.props.options);
    const { options } = this.props;
    // const { jsonData } = options;
    // const secureJsonData = (options.secureJsonData || {}) as MySecureJsonData;

    return (
      <div className="gf-form-group">
        <div className="gf-form">
          <FormField
            label="url"
            labelWidth={6}
            inputWidth={20}
            onChange={this.onUriChange}
            value={options.url || ''}
            placeholder="datasource 'http://example.com:8888/api'"
            tooltip="url to root of API"
          />
        </div>

        {/* <div className="gf-form">
          <FormField
            label="Path"
            labelWidth={6}
            inputWidth={20}
            onChange={this.onPathChange}
            value={jsonData.path || ''}
            placeholder="subpath to root of api. '/examle/api'"
          />
        </div> */}

        {/* <div className="gf-form-inline">
          <div className="gf-form">
            <SecretFormField
              isConfigured={(secureJsonFields && secureJsonFields.apiKey) as boolean}
              value={secureJsonData.apiKey || ''}
              label="API Key"
              placeholder="secure json field (backend only)"
              labelWidth={6}
              inputWidth={20}
              onReset={this.onResetAPIKey}
              onChange={this.onAPIKeyChange}
            />
          </div>
        </div> */}
      </div>
    );
  }
}
