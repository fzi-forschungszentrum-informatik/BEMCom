from django.db import models


class Connector(models.Model):
    name = models.TextField()
    mqtt_topic_logs = models.TextField()
    mqtt_topic_heartbeat = models.TextField()
    mqtt_topic_new_datapoints = models.TextField()
    mqtt_topic_datapoint_map = models.TextField()
    mqtt_topic_messages_prefix = models.TextField()


class DeviceType(models.Model):
    name = models.TextField()


class Device(models.Model):
    connector = models.ForeignKey(
        Connector, on_delete=models.CASCADE
    )
    device_type = models.ForeignKey(
        DeviceType, on_delete=models.CASCADE
    )
    name = models.TextField()
    is_virtual = models.BooleanField()
    x = models.FloatField()
    y = models.FloatField()
    z = models.FloatField()


class Unit(models.Model):
    name = models.TextField()


class Datapoint(models.Model):
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE
    )
    unit = models.ForeignKey(
        Unit, on_delete=models.SET('')
    )
