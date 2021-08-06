import defaults from 'lodash/defaults';

import React, { ChangeEvent, PureComponent } from 'react';
import { Select, InlineFormLabel, LegacyForms } from '@grafana/ui';
import { QueryEditorProps } from '@grafana/data';
import { DataSource } from './DataSource';
import { defaultQuery, MyDataSourceOptions, MyQuery } from './types';

import FormControlLabel from '@material-ui/core/FormControlLabel';
import { Switch, Button, Checkbox } from '@material-ui/core';

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

    custom_user_scaling: false,
    custom_user_name: false,
    changed_input_style: (changed: boolean) => (changed ? { backgroundColor: 'darkslategrey' } : {}),
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
    let datapoint = event;
    onChange({ ...query, datapoint });
    onRunQuery();
  };

  onDatatypeChange = (event: any) => {
    const { onChange, query, onRunQuery } = this.props;
    let datatype = event;
    onChange({ ...query, datatype });
    onRunQuery();
  };

  onDisplayNameChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { onChange, query } = this.props;

    // for updating state for colorful input tracking
    let custom_user_name = this.state.custom_user_name;
    custom_user_name = true;
    this.setState({ ...this.state, custom_user_name });

    let displayName = event.target.value;
    onChange({ ...query, displayName });
  };

  onOffsetChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { onChange, query, onRunQuery } = this.props;
    let offset = event.target.value;
    onChange({ ...query, offset });
    onRunQuery();
  };

  onUseIntervalAndOffset = (event: ChangeEvent<HTMLInputElement>) => {
    const { onChange, query, onRunQuery } = this.props;
    const useIntervalAndOffset = !(event.target.value === 'true');
    onChange({ ...query, useIntervalAndOffset });
    onRunQuery();
  };

  onScalingFactorChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { onChange, query } = this.props;

    // for updating state for colorful input tracking
    let custom_user_scaling = this.state.custom_user_scaling;
    custom_user_scaling = true;
    this.setState({ ...this.state, custom_user_scaling });

    let scalingFactor = parseFloat(event.target.value);
    onChange({ ...query, scalingFactor });
  };

  onUserMetaChange = () => {
    const { onRunQuery } = this.props;

    // for updating state for colorful input tracking
    let custom_user_scaling = this.state.custom_user_scaling;
    custom_user_scaling = false;
    let custom_user_name = this.state.custom_user_name;
    custom_user_name = false;
    this.setState({ ...this.state, custom_user_scaling, custom_user_name });
    onRunQuery();
  };

  onKeyUp = (event: React.KeyboardEvent<HTMLInputElement>): void => {
    // 'keypress' event misbehaves on mobile so we track 'Enter' key via 'keydown' event
    if (event.key === 'Enter') {
      event.preventDefault();
      event.stopPropagation();
      this.onUserMetaChange();
    }
  };

  // Managing queries
  renderQuery(query: MyQuery) {
    return (
      <div style={{ position: 'relative' }}>
        <div className="gf-form-group" style={{ marginBottom: 0, marginTop: 0 }}>
          {/* First Row */}
          <div className="gf-form">
            <div className="gf-form" style={{ marginBottom: 0 }}>
              <InlineFormLabel
                width={10}
                tooltip="Select the datapoint to display. Options are loaded according to the meta data."
              >
                Select Datapoint
              </InlineFormLabel>
              <Select
                width={30}
                placeholder="Select datapoint"
                disabled={query.getMeta}
                value={query.datapoint}
                maxMenuHeight={140}
                // defaultValue={this.state.datapoint_default}
                onChange={e => this.onDatapointChange(e)}
                options={this.state.datapoint_options}
              />
            </div>
            <div className="gf-form" style={{ marginBottom: 0, marginLeft: 4 }}>
              <InlineFormLabel
                width={10}
                tooltip="Select the type of data to display. Options are defined according to BEMCom."
              >
                Select Data Type
              </InlineFormLabel>
              <Select
                width={30}
                placeholder="Select data type"
                disabled={query.getMeta}
                value={query.datatype}
                maxMenuHeight={140}
                // defaultValue={this.state.datatype_options[0]}
                onChange={e => this.onDatatypeChange(e)}
                options={this.state.datatype_options}
              />
            </div>
          </div>

          {/* Optional settigns */}
          <div style={{ backgroundColor: '#0A0A0A', display: 'inline-block' }}>
            {/* Second Row */}
            <div className="gf-form" style={{ marginLeft: 10, marginRight: 10, borderBottom: '1px solid #333333' }}>
              <div className="gf-form" style={{ marginBottom: 0, marginTop: 5 }}>
                <FormField
                  label="Offset"
                  disabled={query.getMeta}
                  labelWidth={8}
                  inputWidth={9}
                  // onKeyUp={this.onKeyUp}
                  onChange={e => this.onOffsetChange(e)}
                  value={query.offset}
                  placeholder="-0 s"
                  tooltip="(optional) set an offset around the timestamps generated through the interval-paremter of grafana's Query options. Example: '-2.5 seconds', '-1 h', '-5 min'"
                />
              </div>
              <div className="gf-form" style={{ marginLeft: 10 }}>
                <FormControlLabel
                  style={{ marginTop: 2 }}
                  control={
                    <Checkbox
                      checked={query.useIntervalAndOffset}
                      value={query.useIntervalAndOffset}
                      onChange={this.onUseIntervalAndOffset}
                      name="useIntervalAndOffset"
                      color="primary"
                      size="small"
                    />
                  }
                  className="m-1"
                  label="use interval and offset"
                />
              </div>
            </div>

            {/* Third Row */}

            <div className="gf-form" style={{ marginLeft: 10, marginRight: 10 }}>
              <span className="gf-form">
                <FormField
                  style={this.state.changed_input_style(this.state.custom_user_name)}
                  label="displayName"
                  disabled={query.getMeta}
                  labelWidth={8}
                  inputWidth={9}
                  onKeyUp={this.onKeyUp}
                  onChange={e => this.onDisplayNameChange(e)}
                  value={query.displayName}
                  placeholder=""
                  tooltip="Custom name for this datapoint"
                />
                <FormField
                  style={this.state.changed_input_style(this.state.custom_user_scaling)}
                  label="scalingFactor"
                  disabled={query.getMeta}
                  type="number"
                  labelWidth={8}
                  inputWidth={5}
                  onKeyUp={this.onKeyUp}
                  onChange={e => this.onScalingFactorChange(e)}
                  value={query.scalingFactor}
                  placeholder=""
                  tooltip="Custom scaling factor for this datapoint"
                />
                <Button
                  style={{ marginTop: 2 }}
                  variant="contained"
                  size="small"
                  disabled={query.getMeta}
                  onClick={this.onUserMetaChange}
                >
                  apply
                </Button>
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  render() {
    const query = defaults(this.props.query, defaultQuery);
    // const { getMeta, datapoint, datatype, displayName, scalingFactor } = query;

    return (
      <div>
        <div className="gf-form" style={{ marginLeft: 0 }}>
          <FormControlLabel
            control={
              <Switch
                checked={query.getMeta}
                value={query.getMeta}
                onChange={this.onMetaChange}
                name="checkedMeta"
                color="primary"
                size="small"
              />
            }
            className="m-1"
            label="Show meta data"
          />
          <FormField
            label="description"
            placeholder="description"
            labelWidth={5}
            inputWidth={30}
            value={query.datapoint.description || ''}
            disabled={true}
          />
        </div>

        {this.renderQuery(query)}
      </div>
    );
  }
}
