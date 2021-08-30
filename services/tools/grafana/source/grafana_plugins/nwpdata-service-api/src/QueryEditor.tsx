import defaults from 'lodash/defaults';

import React, { FormEvent, ChangeEvent, PureComponent } from 'react';
import { Field, Checkbox, TextArea } from '@grafana/ui';
import { Button } from '@material-ui/core';
import { QueryEditorProps } from '@grafana/data';
import { DataSource } from './DataSource';
import { defaultQuery, MyDataSourceOptions, MyQuery } from './types';

type Props = QueryEditorProps<DataSource, MyQuery, MyDataSourceOptions>;

export class QueryEditor extends PureComponent<Props> {
  state = {};

  async componentDidMount() {}

  onKeyUp = (event: React.KeyboardEvent<HTMLInputElement>): void => {
    // 'keypress' event misbehaves on mobile so we track 'Enter' key via 'keydown' event
    if (event.key === 'Enter') {
      event.preventDefault();
      event.stopPropagation();
      this.onRunQuery();
    }
  };

  onRequestParamsJson = (event: FormEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { onChange, query } = this.props;
    const { value } = event.target as HTMLInputElement | HTMLTextAreaElement;
    // for updating state for colorful input tracking
    let requestParamsJson = value;
    onChange({ ...query, requestParamsJson });
  };

  onNameSettingsJsonChange = (event: FormEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { onChange, query } = this.props;
    const { value } = event.target as HTMLInputElement | HTMLTextAreaElement;
    // for updating state for colorful input tracking
    let nameSettingsJson = value;
    onChange({ ...query, nameSettingsJson });
  };

  onFilterByNamesChanged = (event: ChangeEvent<HTMLInputElement>) => {
    const { onChange, query, onRunQuery } = this.props;
    const filterByNames = event.target.checked;
    onChange({ ...query, filterByNames });
    onRunQuery();
  };

  onRunQuery = () => {
    const { onRunQuery } = this.props;
    onRunQuery();
  };

  // Managing queries
  renderQuery(query: MyQuery) {
    return (
      <div style={{ position: 'relative' }}>
        <div className="gf-form-group" style={{ marginBottom: 0, marginTop: 0 }}>
          {/* First Row */}
          <div className="gf-form" style={{ marginBottom: 0, marginTop: 5 }}>
            <Field label="Query" description="Define your query in accordance with the service's parameters">
              <TextArea
                name="query"
                onChange={(e) => this.onRequestParamsJson(e)}
                value={query.requestParamsJson}
                placeholder='
                {
                  "start_timestamp": "2021-08-04T10:39:37.639121+00:00",
                  "end_timestamp": "2021-08-04T12:39:37.639130+00:00",
                  ...
                }'
                required
                style={{ width: 600, height: 160 }}
              />
            </Field>
            <div style={{ marginLeft: 20 }}>
              <Field label="Fieldnames" description="Define custom names for specific fields">
                <TextArea
                  name="settings"
                  onChange={(e) => this.onNameSettingsJsonChange(e)}
                  value={query.nameSettingsJson}
                  placeholder='
                {
                  "yhat": "mean",
                  "yhat_lower": "5.5 % quantile",
                  "yhat_upper": "94.5 % quantile",
                  ...
                }'
                  style={{ width: 400, height: 160 }}
                />
              </Field>
            </div>
          </div>
          <Checkbox
            label="filter by provided names"
            checked={query.filterByNames}
            value={query.filterByNames}
            onChange={this.onFilterByNamesChanged}
            name="filterBynames"
            color="primary"
          />
          <div className="gf-form" style={{ marginBottom: 0, marginTop: 5 }}>
            <Button style={{ marginTop: 2 }} variant="contained" size="small" onClick={this.onRunQuery}>
              run
            </Button>
          </div>
        </div>
      </div>
    );
  }

  render() {
    const query = defaults(this.props.query, defaultQuery);
    // const { getMeta, datapoint, datatype, displayName, scalingFactor } = query;

    return <div>{this.renderQuery(query)}</div>;
  }
}
