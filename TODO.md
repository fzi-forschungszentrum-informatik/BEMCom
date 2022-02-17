# ToDos

* [ ] Services

  * [ ] API
    * [ ] Django
      * [ ] Alerting (E-Mail) on 500 status code.
      * [ ] Collect (and test) code for changes in datapoint at central location and add tests. Is currently distributed over api_admin_ui and api_main.signals
      * [ ] Find solution if example value is NaN,+Inf or - Inf. Maybe just a try except and store these as text?
      * [ ] Alerting (Prom AlertManager) if datapoint values have certain values or have not been updated for a certain time.
      * [ ] Document return objects and codes for errors of REST interface.
      * [ ] Add Websocket Push Interface.
      * [ ] Fix adding Controller Admin Pages, there seems to be while defining controlled_datapoints.
      * [ ] Extend documentation on REST and UI Endpoints
  * [ ] Controllers
    * [ ] Python
      * [ ] Rename to something more goal oriented, i.e. that describes rather what the controller does.
  * [ ] Monitors:
    * [ ] Move MQTT message monitor to Tools
