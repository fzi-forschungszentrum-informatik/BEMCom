import defaults from 'lodash/defaults';

import React, { ChangeEvent, PureComponent } from 'react';
import { Select, InlineFormLabel, LegacyForms } from '@grafana/ui';
import { QueryEditorProps } from '@grafana/data';
import { DataSource } from './DataSource';
import { defaultQuery, MyDataSourceOptions, MyQuery } from './types';

import FormControlLabel from '@material-ui/core/FormControlLabel';
import { Switch, Button } from '@material-ui/core';
import DeleteIcon from '@material-ui/icons/Delete';
import AddIcon from '@material-ui/icons/Add';

import { getBackendSrv } from '@grafana/runtime';
const { FormField } = LegacyForms;

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
      { label: 'setpoint', value: 2, description: 'latest setpoint' },
    ],
  };

  async componentDidMount() {
    // query backend meta to get options.
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

  onDisplayNameChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { onChange, query } = this.props;
    const displayName = event.target.value;
    onChange({ ...query, displayName });
  };

  onScalingFactorChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { onChange, query } = this.props;
    const sf = parseFloat(event.target.value);
    onChange({ ...query, scalingFactor: sf });
  };

  onUserMetaChange = (event: any) => {
    const { onRunQuery } = this.props;
    onRunQuery();
  };

  render() {
    const query = defaults(this.props.query, defaultQuery);
    const { getMeta } = query;

    return (
      <div>
        <div style={{ position: 'relative' }}>
          <div className="gf-form-group">
            {/* First Row */}
            <div className="gf-form">
              <div className="gf-form">
                <InlineFormLabel
                  width={10}
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
                <InlineFormLabel width={10} tooltip="Select the data to display.">
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

              <div className="gf-form" style={{ marginLeft: 20 }}>
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
            </div>

            {/* Second Row */}

            <div className="gf-form" style={{ marginLeft: 20 }}>
              <span className="gf-form">
                <FormField
                  label="displayName"
                  disabled={getMeta}
                  labelWidth={8}
                  inputWidth={10}
                  onChange={this.onDisplayNameChange}
                  value={query.displayName || ''}
                  placeholder=""
                  tooltip="custom name for the data point"
                />
                <FormField
                  label="scalingFactor"
                  disabled={getMeta}
                  type="number"
                  labelWidth={8}
                  inputWidth={10}
                  onChange={this.onScalingFactorChange}
                  value={query.scalingFactor || ''}
                  placeholder=""
                  tooltip="custom scaling factor to apply to the data"
                />
                <Button variant="contained" size="small" disabled={getMeta} onClick={this.onUserMetaChange}>
                  apply
                </Button>
              </span>
            </div>
          </div>

          {/* Button on Right side */}

          <div style={{ position: 'absolute', top: 20, right: 20 }}>
            <Button style={{ backgroundColor: 'grey' }} variant="outlined" size="small">
              <DeleteIcon />
            </Button>
            <Button style={{ backgroundColor: 'grey' }} variant="outlined" size="small">
              <AddIcon />
            </Button>
          </div>
        </div>
      </div>
    );
  }
}
