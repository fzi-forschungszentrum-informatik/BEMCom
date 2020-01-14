from django.db.models import signals
from django.dispatch import receiver, Signal

from admin_interface.models import Connector
from admin_interface.models import ConnectorDatapointTopicMapper
from admin_interface.models import GenericDatapoint
from admin_interface.connector_mqtt_integration import ConnectorMQTTIntegration

subscription_status = Signal(providing_args=['subscribed'])#['datapoint_key_in_connector', 'mqtt_topic', 'subscribed'])

@receiver(signals.post_save, sender=ConnectorDatapointTopicMapper)
def subscribe_to_mapped_datapoint_topic(**kwargs):
    """
    TODO: Currently, client subscribes to all topics of a newly added connector including all datapoint messages
        (see integrate_new_connector() in connector_mqtt_integration module).
        -> subscription management of selected messages is missing.
    """
    # kwargs contains sender, instance, update_fields (and some other args)
    if kwargs['update_fields']:
        if 'subscribed' in kwargs['update_fields']:
            mapping = kwargs['instance']
            connector = getattr(mapping, 'connector')
            topic = getattr(mapping, 'mqtt_topic')
            key = getattr(mapping, 'datapoint_key_in_connector')
            new_subscription_status = getattr(mapping, 'subscribed')

            # Update subscription status of mapped available datapoint
            GenericDatapoint.objects.filter(
                connector=connector,
                datapoint_key_in_connector=key).update(subscribed=new_subscription_status)
            print("Subscription status changed.")

import logging
logger = logging.getLogger(__name__)

@receiver(signals.post_save, sender=Connector)
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
