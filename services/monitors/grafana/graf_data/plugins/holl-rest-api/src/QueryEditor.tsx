import defaults from 'lodash/defaults';

import React, { ChangeEvent, PureComponent } from 'react';
import { Select, InlineFormLabel } from '@grafana/ui';
import { QueryEditorProps } from '@grafana/data';
import { DataSource } from './DataSource';
import { defaultQuery, MyDataSourceOptions, MyQuery } from './types';

import FormControlLabel from '@material-ui/core/FormControlLabel';
import { Switch } from '@material-ui/core';

import { getBackendSrv } from '@grafana/runtime';

// const { FormField } = LegacyForms;

type Props = QueryEditorProps<DataSource, MyQuery, MyDataSourceOptions>;

export class QueryEditor extends PureComponent<Props> {
  state = {
    showMeta: false,
    datapoint_options: [
      { label: 'example option 1', value: 1, description: 'example description' },
      { label: 'example option 2', value: 2, description: 'example description' },
      // { imgUrl: 'https://placekitten.com/40/40', },
    ],

    datatype_options: [
      { label: 'value', value: 0, description: 'timeseries of values' },
      { label: 'schedule', value: 1, description: 'currently active schedule' },
      { label: 'setpoint upper', value: 2, description: 'uppder bound of latest setpoint' },
      { label: 'setpoint lower', value: 2, description: 'lower bound of latest setpoint' },
    ],
  };

  async componentDidMount() {
    console.log('COmponent - mounted!');
    // query backend meta to get options.
    console.log('requesting meta url: ', this.props.datasource.url + '/datapoint');
    try {
      const result = await getBackendSrv().datasourceRequest({
        method: 'GET',
        url: this.props.datasource.url + '/datapoint/',
      });

      let datapoint_options: any = [];

      result.data.forEach((option: any) => {
        datapoint_options.push({
          label: option.short_name,
          value: option.id,
          description: option.description,
        });

        this.setState({ datapoint_options });
      });
    } catch (error) {
      console.log('Error when requesting meta data from datasource: ', error);
    }
  }

  onMetaChange = (event: ChangeEvent<HTMLInputElement>, child: boolean) => {
    console.log('changed select: event:', event);
    console.log('changed select: child:', child);

    const { onChange, query, onRunQuery } = this.props;
    let s = { ...this.state };
    s.showMeta = child;
    this.setState({ s });
    onChange({ ...query, getMeta: child });
    onRunQuery();
  };

  onDatapointChange = (event: any) => {
    const { onChange, query, onRunQuery } = this.props;

    // change query and execute
    onChange({ ...query, datapoint: event });
    onRunQuery();
  };

  onDatatypeChange = (event: any) => {
    const { onChange, query, onRunQuery } = this.props;

    // change query and execute
    onChange({ ...query, datatype: event });
    onRunQuery();
  };

  // onQueryTextChange = (event: any) => {
  //   const { onChange, query } = this.props;
  //   onChange({ ...query, queryText: event.target.value });
  // };

  // onConstantChange = (event: ChangeEvent<HTMLInputElement>) => {
  //   const { onChange, query, onRunQuery } = this.props;
  //   onChange({ ...query, constant: parseFloat(event.target.value) });
  //   // executes the query
  //   onRunQuery();
  // };

  render() {
    const query = defaults(this.props.query, defaultQuery);
    const { getMeta } = query;

    return (
      <div>
        <div className="gf-form">
          <FormControlLabel
            control={
              <Switch
                checked={getMeta}
                value={getMeta}
                onChange={this.onMetaChange}
                name="checkedMeta"
                color="primary"
                size="small"
              />
            }
            className="m-1"
            label="Show meta data"
          />
        </div>

        <div className="gf-form-group">
          <div className="gf-form">
            <div className="gf-form">
              <InlineFormLabel
                width={15}
                tooltip="Select the datapoint to display. Options are loaded according to the meta data."
              >
                Select Datapoint
              </InlineFormLabel>
              <Select
                width={30}
                placeholder="Select datapoint"
                disabled={getMeta}
                value={this.props.query.datapoint}
                maxMenuHeight={140}
                // defaultValue={this.state.datapoint_default}
                onChange={this.onDatapointChange}
                options={this.state.datapoint_options}
              />
            </div>
            <div className="gf-form">
              <InlineFormLabel width={15} tooltip="Select the data to display.">
                Select Data Type
              </InlineFormLabel>
              <Select
                width={30}
                placeholder="Select data type"
                disabled={getMeta}
                value={this.props.query.datatype}
                maxMenuHeight={140}
                // defaultValue={this.state.datatype_options[0]}
                onChange={this.onDatatypeChange}
                options={this.state.datatype_options}
              />
            </div>
          </div>
        </div>

        {/* <div className="gf-form">
          <FormField
            width={4}
            value={constant}
            onChange={this.onConstantChange}
            label="Constant"
            type="number"
            step="0.1"
            disabled={getMeta}
          />
          <FormField
            labelWidth={8}
            value={queryText || ''}
            onChange={this.onQueryTextChange}
            label="Query Text"
            tooltip="Not used yet"
            disabled={getMeta}
          />
        </div> */}
      </div>
    );
  }
}
