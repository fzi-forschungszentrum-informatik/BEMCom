from django.db.models import signals
from django.dispatch import receiver

from .models.connector import Connector
from .models.datapoint import Datapoint
from .connector_mqtt_integration import ConnectorMQTTIntegration


@receiver(signals.post_save, sender=Datapoint)
@receiver(signals.post_delete, sender=Datapoint)
@receiver(signals.post_delete, sender=Connector)
@receiver(signals.post_save, sender=Connector)
def update_connector_mqtt_integration_settings(sender, instance, **kwargs):
    """
    Trigger update of subscribed topics if changes in Connector DB occure.

    The `special_connector_name` is used during tests for a special case
    where we do not want the signal to be fired, i.e. as the connector is added
    before the ConnectorMQTTIntegration is set up.

    See the ConnectorMQTTIntegration class for more documentation.
    """
    special_connector_name = (
        "the_only_connector_name_that_won't_fire_the_signal"
    )
    if sender == Connector:
        if instance.name != special_connector_name:
            cmi = ConnectorMQTTIntegration.get_instance()
            cmi.update_topics()
            cmi.update_subscriptions()
    # TODO Reactivate once fake mqtt is able to unsubscribe as tests will
    # fail else.
#    if sender == models.Datapoint:
#        cmi = ConnectorMQTTIntegration.get_instance()
#        cmi.update_topics()
#        cmi.update_subscriptions()


@receiver(signals.post_save, sender=Datapoint)
@receiver(signals.post_delete, sender=Datapoint)
@receiver(signals.post_save, sender=Connector)
def trigger_datapoint_map_update(sender, instance, **kwargs):
    """
    Trigger that a new datapoint map is created and sent on changes.

    This is required if ether the Connector is saved, (as the name could have
    been changed and with it the MQTT topics), or if the `data_format` value of
    a Datatpoint object is changed, or if a Datapoint is deleted.

    TODO: This deserves an additional logic tests.
          However it is already tested as part of an integration test
          TestUpdateSubscription.test_datapoint_message_received in
          tests/test_mqtt_integration.py
    """
    special_connector_name = (
        "the_only_connector_name_that_won't_fire_the_signal"
    )

    cmi = ConnectorMQTTIntegration.get_instance()
    if sender == Connector:
        if instance.name == special_connector_name:
            return

        # If in doubt if name could have been changed better create a new
        # datapoint_map.
        cmi.create_and_send_datapoint_map(connector=instance)

    if sender == Datapoint:
        connector = instance.connector
        # If Datapoint is saved.
        if "update_fields" in kwargs:
            uf = kwargs["update_fields"]
            # Trigger update if we ether do not know what fields have been
            # changed, if id has changed as this affects the mqtt_topic or
            # if we data_fromat has changed as this might have an affect wether
            # the datapoint is in datapoint_map or not.
            if uf is None or "id" in uf or "is_active" in uf:
                cmi.create_and_send_datapoint_map(connector=connector)
        # If Datapoint is deleted.
        else:
            cmi.create_and_send_datapoint_map(connector=connector)
