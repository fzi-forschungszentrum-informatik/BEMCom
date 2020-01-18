from django.db.models import signals
from django.dispatch import receiver

from admin_interface import models
from admin_interface.connector_mqtt_integration import ConnectorMQTTIntegration

@receiver(signals.post_save, sender=models.Connector)
def update_connector_mqtt_integration_settings(**kwargs):
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
    if kwargs["instance"].name != special_connector_name:
        cmi = ConnectorMQTTIntegration.get_instance()
        cmi.update_topics()
        cmi.update_subscriptions()
