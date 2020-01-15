from django.db.models import signals
from django.dispatch import receiver, Signal
from .models import ConnectorAvailableDatapoints
from admin_interface import connector_mqtt_integration

#subscription_status = Signal(providing_args=['subscribed'])#['datapoint_key_in_connector', 'mqtt_topic', 'subscribed'])


# @receiver(signals.post_save, sender=ConnectorDatapointTopicMapper)
# def subscribe_to_mapped_datapoint_topic(**kwargs):
#         """
#         TODO: Keep for now as reference for possible similar implementation
#             -> delete if not needed anymore
#         """
#     """
#     TODO: Currently, client subscribes to all topics of a newly added connector including all datapoint messages
#         (see integrate_new_connector() in connector_mqtt_integration module).
#         -> subscription management of selected messages is missing.
#     """
#     # kwargs contains sender, instance, update_fields (and some other args)
#     if kwargs['update_fields']:
#         if 'subscribed' in kwargs['update_fields']:
#             mapping = kwargs['instance']
#             connector = getattr(mapping, 'connector')
#             topic = getattr(mapping, 'mqtt_topic')
#             key = getattr(mapping, 'datapoint_key_in_connector')
#             new_subscription_status = getattr(mapping, 'subscribed')
#
#             # Update subscription status of mapped available datapoint
#             ConnectorAvailableDatapoints.objects.filter(
#                 connector=connector,
#                 datapoint_key_in_connector=key).update(subscribed=new_subscription_status)
#             print("Subscription status changed.")


