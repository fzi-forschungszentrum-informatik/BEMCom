#!/usr/bin/env python3
"""
"""
import os
import sys
from datetime import datetime, timezone
import json
import logging
from random import random
import socket
from time import sleep

from esg.api_client.base import HttpBaseClient
from esg.api_client.emp import EmpClient
from esg.models.datapoint import DatapointList
from esg.models.datapoint import ValueMessage
from esg.models.datapoint import ValueMessageByDatapointId
from paho.mqtt.client import Client
from pyconnector_template.dispatch import DispatchInInterval
from pyconnector_template.dispatch import DispatchOnce

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s"
)
logger = logging.getLogger(__name__)


class EmpLink:
    """
    All the logic to push data from BEMCom to EMP.
    """

    def __init__(self, mqtt_client=Client):
        """
        Load configuration from environment variables and connect to BEMCom
        and EMP.
        """
        self.origin = os.getenv("ORIGIN")

        logger.info("Starting up EMP Link (ORIGIN: {})".format(self.origin))

        if not self.origin:
            raise ValueError("Environment variable `ORIGIN` can't be empty!")

        emp_api_url = os.getenv("EMP_API_URL")
        emp_api_verify_ssl = True
        if (os.getenv("EMP_API_VERIFY_SSL") or "TRUE").lower() == "false":
            emp_api_verify_ssl = False
        emp_api_username = os.getenv("EMP_API_USERNAME")
        emp_api_password = os.getenv("EMP_API_PASSWORD")
        self.emp_client = EmpClient(
            base_url=emp_api_url,
            verify=emp_api_verify_ssl,
            username=emp_api_username,
            password=emp_api_password,
        )

        logger.info("Testing connection to EMP API at {}".format(emp_api_url))
        self.emp_client.test_connection()

        bemcom_api_url = os.getenv("BEMCOM_API_URL")
        bemcom_api_verify_ssl = True
        if (os.getenv("BEMCOM_API_VERIFY_SSL") or "TRUE").lower() == "false":
            bemcom_api_verify_ssl = False
        bemcom_api_username = os.getenv("BEMCOM_API_USERNAME")
        bemcom_api_password = os.getenv("BEMCOM_API_PASSWORD")
        self.bemcom_client = HttpBaseClient(
            base_url=bemcom_api_url,
            verify=bemcom_api_verify_ssl,
            username=bemcom_api_username,
            password=bemcom_api_password,
        )

        logger.info(
            "Testing connection to BEMCom API at {}".format(bemcom_api_url)
        )
        _ = self.bemcom_client.get("/")

        # The configuration for (re)connecting to the broker.
        self.connect_kwargs = {
            "host": os.getenv("MQTT_BROKER_HOST"),
            "port": int(os.getenv("MQTT_BROKER_PORT") or 1883),
        }

        # The private userdata, used by the callbacks.
        userdata = {
            "connect_kwargs": self.connect_kwargs,
            "self": self,
        }
        self.userdata = userdata

        self.client = mqtt_client(userdata=userdata)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        # Initial connection to broker.
        try:
            self.client.connect(**self.connect_kwargs)
        except (socket.gaierror, OSError):
            logger.error(
                "Cannot connect to MQTT broker: %s. Aborting startup.",
                self.connect_kwargs,
            )
            sys.exit(1)

        # This is the list of topics the client is subscribed to.
        self._subsribed_topics = []

    @staticmethod
    def on_connect(client, userdata, flags, rc):
        logger.info(
            "Connected to MQTT broker tcp://%s:%s",
            userdata["connect_kwargs"]["host"],
            userdata["connect_kwargs"]["port"],
        )

    @staticmethod
    def on_disconnect(client, userdata, rc):
        """
        Atempt Reconnecting if disconnect was not called from a call to
        client.disconnect().
        """
        if rc != 0:
            logger.info(
                "Lost connection to MQTT broker with code %s. Reconnecting", rc
            )
            client.connect(**userdata["connect_kwargs"])

    @staticmethod
    def on_message(client, userdata, msg):
        """
        Push the message forward to the EMP.
        """
        self = userdata["self"]

        logger.debug("on_message received msg with topic %s" % msg.topic)

        msg_origin_id, msg_type = msg.topic.split("/")[-2:]

        # Check if know this message id already, and if not trigger a
        # datapoint update as this message should usually only be published
        # if in datapoint metadata too.
        if msg_origin_id not in userdata["datapoint_id_map"]:
            self.update_datapoint_and_subscriptions()
        if msg_origin_id not in userdata["datapoint_id_map"]:
            logger.error(
                "Datapoint (id: {}) isn't known in BEMCom DB.".format(
                    msg_origin_id
                )
            )

        # Quick exit for those message for which no handling is implemented
        # below.
        if msg_type != "value":
            logger.warning(
                "Received unsupported message on topic: %s" % msg.topic
            )
            return
        try:
            payload_json_str = msg.payload.decode()
            # Quick fix, some datapoint seem to publish NaN values. This is
            # no valid JSON!
            payload_json_str = payload_json_str.replace('"nan"', "null")

            # Also note that the messages on the broker are normal JSON, not
            # the JSON model that has a JSON field as value.
            payload_python = json.loads(payload_json_str)
            payload_python["value"] = json.dumps(payload_python["value"])

            # Now we can parse it with the Pydantic model.
            payload_pydantic = ValueMessage.parse_obj_bemcom(payload_python)
        except Exception:
            logger.exception(
                "Error encoutered while parsing BEMCom message from broker: {}"
                "".format(msg.payload)
            )

        msg_dict = payload_pydantic.dict()
        emp_id = userdata["datapoint_id_map"][msg_origin_id]

        # use construct_recursive only if you are sure that the values
        # are correct and match the message format.
        value_msgs_by_dp_id = ValueMessageByDatapointId.construct_recursive(
            __root__={emp_id: msg_dict}
        )

        # Push to EMP.
        put_summary = self.emp_client.put_datapoint_value_latest(
            value_msgs_by_dp_id=value_msgs_by_dp_id
        )

        logger.debug(
            "Put value messages latest: {} updated, {} created."
            "".format(put_summary.objects_updated, put_summary.objects_created)
        )

    def update_datapoint_and_subscriptions(self):
        """
        Fetch the latest metadata, update the EMP and MQTT subscriptions.

        Stores in userdata:
        --------------------
        datapoint_id_map: dict
            Mapping from datapoint IDs of BEMCom to datapoint IDs of EMP.
        """
        datapoints = self.bemcom_client.get("/datapoint/").json()

        # Prepare the messages for the EMP.
        for datapoint in datapoints:
            datapoint["origin_id"] = datapoint.pop("id")
            datapoint["origin"] = self.origin
            # Adapt fields too
            # E.g. `generic_text` -> "Generic Text"
            datapoint["type"] = datapoint["type"].replace("_", " ").title()
            data_format = datapoint["data_format"]
            datapoint["data_format"] = data_format.replace("_", " ").title()
            # make Bool -> Boolean as the Enum entry looks like this:
            # bool = "Boolean"
            if datapoint["data_format"] == "Bool":
                datapoint["data_format"] = "Boolean"

        # API expects a list of datapoints.
        datapoint_list = DatapointList.parse_obj({"__root__": datapoints})

        # Push to EMP, this returns the datapoint metadata as confirmation.
        datapoint_list = self.emp_client.put_datapoint_metadata_latest(
            datapoint_list=datapoint_list
        )

        logger.info(
            "Pushed metadata of {} datapoints to EMP."
            "".format(len(datapoints))
        )

        # Make a map between internal EMP IDs and EMP IDs.
        datapoint_id_map = {}
        for datapoint_obj in datapoint_list.__root__:
            emp_id = datapoint_obj.id
            datapoint_id_map[datapoint_obj.origin_id] = emp_id

        self.userdata["datapoint_id_map"] = datapoint_id_map
        logger.debug(
            "Updated datapoint ID map: {}".format(
                self.userdata["datapoint_id_map"]
            )
        )

        # Compute the topics
        topics = []
        connector_names = {dp["connector"]["name"] for dp in datapoints}
        for connector_name in connector_names:
            topic = "{}/messages/#".format(connector_name)
            if topic not in self._subsribed_topics:
                logger.info("Subscribing to topic: {}".format(topic))
                self.client.subscribe(topic)
                self._subsribed_topics.append(topic)

        return datapoint_id_map, topics

    def update_values(self):
        """
        Usually measured values would be received from some device or
        hardware abstraction component. Here we just compute a random
        value on every call to simulate activity.
        """

        value_msg_internal_id = "42"
        value_message = {
            "value": round(22 + random() * 3, 1),
            "time": datetime.utcnow().astimezone(timezone.utc),
        }

        # get EMP ID if the corresponding datapoint.
        emp_id = self.datapoint_id_map[value_msg_internal_id]

        # use construct_recursive only if you are sure that the values
        # are correct and match the message format.
        value_msgs_by_dp_id = ValueMessageByDatapointId.construct_recursive(
            __root__={emp_id: value_message}
        )

        # Push to EMP.
        put_summary = self.emp_client.put_datapoint_value_latest(
            value_msgs_by_dp_id=value_msgs_by_dp_id
        )

        logger.info(
            "Put value messages latest: {} updated, {} created."
            "".format(put_summary.objects_updated, put_summary.objects_created)
        )

    @staticmethod
    def mqtt_worker(mqtt_client):
        """
        Execute the MQTT main loop in a dedicated thread. This is
        similar to use loop_start of paho mqtt but allows us to use a
        unfied concept to check whether all background processes are
        still alive.
        """
        try:
            mqtt_client.loop_forever()
        finally:
            # Gracefully terminate connection once the main program exits.
            mqtt_client.disconnect()

    def main(self):
        """
        Just check for changes in datapoint metadata periodically.

        Everything else is handled by the `on_message` method.
        """

        logger.debug("Starting MQTT dispatcher with client loop.")
        mqtt_dispatcher = DispatchOnce(
            target_func=self.mqtt_worker,
            target_kwargs={"mqtt_client": self.client},
        )
        mqtt_dispatcher.start()

        # Trigger a push of the latest datapoint metadata to EMP
        # every minute.
        datapoint_update_dispatcher = DispatchInInterval(
            call_interval=60,
            target_func=self.update_datapoint_and_subscriptions,
        )
        datapoint_update_dispatcher.start()

        # This collects all running dispatchers. These are checked for health
        # in the main loop below.
        dispatchers = [mqtt_dispatcher, datapoint_update_dispatcher]

        logger.info("EMP link online. Entering main loop.")
        try:
            while True:
                # Check that all dispatchers are alive, and if this is the
                # case assume that the connector operations as expected.
                if not all([d.is_alive() for d in dispatchers]):
                    # If one is not alive, see if we encountered an exception
                    # and raise it, as exceptions in threads are not
                    # automatically forwarded to the main program.
                    for d in dispatchers:
                        if d.exception is not None:
                            raise d.exception
                    # If no exception is found raise a custom on.
                    raise RuntimeError(
                        "At least one dispatcher thread is not alive, but no "
                        "exception was caught."
                    )

                    break
                sleep(1)

        except (KeyboardInterrupt, SystemExit):
            # This is the normal way to exit the Connector. No need to log the
            # exception.
            logger.info(
                "EMP link received KeyboardInterrupt or SystemExit"
                ", shuting down."
            )
        except Exception:
            # This is execution when something goes really wrong.
            logger.exception(
                "EMP link main loop has caused an unexpected exception. "
                "Shuting down."
            )
        finally:
            for dispatcher in dispatchers:
                # Ask the dispatcher (i.e. thread) to quit and give it
                # one second to execute any cleanup. Anything that takes
                # longer will be killed hard once the main program exits
                # as the dispatcher thread is expected to be a daemonic
                # thread.
                logger.debug("Terminating dispatcher %s", dispatcher)
                if dispatcher.is_alive():
                    dispatcher.terminate()
                dispatcher.join(1)
            logger.info("EMP link shut down completed. Good bye.")


if __name__ == "__main__":
    emp_link = EmpLink()
    emp_link.main()
