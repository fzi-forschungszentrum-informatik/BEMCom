import logging

from django.db.models import signals
from django.dispatch import receiver

from .models.connector import Connector
from .models.datapoint import Datapoint
from .models.controller import Controller, ControlledDatapoint
from .mqtt_integration import ApiMqttIntegration


logger = logging.getLogger(__name__)


@receiver(signals.pre_delete, sender=Connector)
def trigger_clear_datapoint_map(sender, instance, **kwargs):
    """
    If we just delete the Connector object the connector service will not
    see any update to datapoint_map, and hence continue to push data
    about the previously selected datapoints. Here we send an empty datapoint
    map, before we delete to reset all selected datapoints for the connector.

    TODO: This deserves a test
    """
    ami = ApiMqttIntegration.get_instance()
    if ami is None:
        logger.warning(
            "Could not trigger clear_datapoint_map."
            "of MqttToDb. ApiMqttIntegration is not running."
        )
        return
    ami.trigger_clear_datapoint_map(connector_id=instance.id)


@receiver(signals.post_save, sender=Datapoint)
@receiver(signals.post_delete, sender=Datapoint)
@receiver(signals.post_save, sender=Connector)
def trigger_datapoint_map_update(sender, instance, **kwargs):
    """
    Trigger that a new datapoint map is created and sent on changes.

    This is required if ether the Connector is saved, (as the name could have
    been changed and with it the MQTT topics) or if a Datapoint is deleted.

    TODO: This deserves a test.
    """
    if sender == Connector:
        connector_id = instance.id

    if sender == Datapoint:
        connector_id = instance.connector.id

        # If Datapoint is saved check if we can skip the datapoint map update
        # as the relevant fields, i.e. is_active and id (for the topic) have
        # not changed.
        if "update_fields" in kwargs and kwargs["update_fields"] is not None:
            uf = kwargs["update_fields"]
            if "id" not in uf and "is_active" not in uf:
                return

    ami = ApiMqttIntegration.get_instance()
    if ami is None:
        logger.warning(
            "Could not trigger datapoint_map_update."
            "of MqttToDb. ApiMqttIntegration is not running."
        )
        return
    ami.trigger_create_and_send_datapoint_map(connector_id=connector_id)


@receiver(signals.post_save, sender=Datapoint)
@receiver(signals.post_delete, sender=Datapoint)
@receiver(signals.post_delete, sender=Connector)
@receiver(signals.post_save, sender=Connector)
def trigger_update_topics_and_subscriptions(sender, instance, **kwargs):
    """
    Trigger update of subscribed topics if changes in Connector DB occur.

    See the ApiMqttIntegration class for more documentation.

    TODO: This needs a test.
    """
    # Trigger updates of topics only if the topic could have changed, i.e.
    # the id has changed or we don't know which files have been changed.
    if sender == Datapoint:
        if "update_fields" in kwargs and kwargs["update_fields"] is not None:
            uf = kwargs["update_fields"]
            if "id" not in uf and "is_active" not in uf:
                return

    ami = ApiMqttIntegration.get_instance()
    if ami is None:
        logger.warning(
            "Could not trigger update_topics_and_subscriptions "
            "of MqttToDb. ApiMqttIntegration is not running."
        )
        return
    ami.trigger_update_topics_and_subscriptions()


@receiver(signals.post_save, sender=ControlledDatapoint)
@receiver(signals.post_delete, sender=ControlledDatapoint)
@receiver(signals.post_save, sender=Controller)
def trigger_create_and_send_controlled_datapoints(sender, instance, **kwargs):
    """
    Compute an update of configuration data for the controllers.

    This is ether necessary if the MQTT topic of the controller has changed
    or if a ControlledDatapoint object has been changed.

    TODO: This needs a test.
    """
    if sender == Controller:
        controller_id = instance.id
    elif sender == ControlledDatapoint:
        controller_id = instance.controller.id

    ami = ApiMqttIntegration.get_instance()
    if ami is None:
        logger.warning(
            "Could not trigger create_and_send_controlled_datapoints "
            "of MqttToDb. ApiMqttIntegration is not running."
        )
        return
    ami.trigger_create_and_send_controlled_datapoints(
        controller_id=controller_id
    )
