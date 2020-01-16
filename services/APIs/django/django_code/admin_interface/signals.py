from django.db.models import signals
from django.dispatch import receiver, Signal
from .models import ConnectorAvailableDatapoints, NumericDatapoint, TextDatapoint
from admin_interface import connector_mqtt_integration

#subscription_status = Signal(providing_args=['subscribed'])#['datapoint_key_in_connector', 'mqtt_topic', 'subscribed'])


# @receiver(signals.post_save, sender=ConnectorDatapointTopicMapper)
# def subscribe_to_mapped_datapoint_topic(**kwargs):
#         """
#         TODO: Keep for now as reference for possible similar implementation
#             -> delete if not needed anymore
#         """
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


@receiver(signals.post_save, sender=ConnectorAvailableDatapoints)
def create_datapoint(**kwargs):
    """
    @david: quick and dirty solution for dev, I assume you have a more elegant solution -> can be removed
    """

    # kwargs contains sender, instance, update_fields (and some other args)
    if kwargs['update_fields']:
        if 'format' in kwargs['update_fields']:
            available_datapoint = kwargs['instance']
            connector = getattr(available_datapoint, 'connector')
            key = getattr(available_datapoint, 'datapoint_key_in_connector')
            dp_format = getattr(available_datapoint, 'format')

            # TODO: case 'unused'
            if dp_format == 'num':
                _ = NumericDatapoint(
                    connector=connector,
                    datapoint_key_in_connector=key,
                ).save()

                if TextDatapoint.objects.filter(
                    connector=connector,
                    datapoint_key_in_connector=key
                ).exists():
                    TextDatapoint.objects.filter(
                        connector=connector,
                        datapoint_key_in_connector=key
                    ).delete()
            elif dp_format == 'text':
                _ = TextDatapoint(
                    connector=connector,
                    datapoint_key_in_connector=key,
                ).save()

                if NumericDatapoint.objects.filter(
                    connector=connector,
                    datapoint_key_in_connector=key
                ).exists():
                    NumericDatapoint.objects.filter(
                        connector=connector,
                        datapoint_key_in_connector=key
                    ).delete()

