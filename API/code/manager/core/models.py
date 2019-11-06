from django.db import models


class Connector(models.Model):
    """
    TODO: Ensure that all topics are unique.
    """
    name = models.TextField()
    mqtt_topic_logs = models.TextField()
    mqtt_topic_heartbeat = models.TextField()
    mqtt_topic_available_datapoints = models.TextField()
    mqtt_topic_datapoint_map = models.TextField()


class ConnectorLogEntry(models.Model):
    connector = models.ForeignKey(
        Connector, on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField()
    msg = models.TextField()
    emitter = models.TextField()
    level = models.SmallIntegerField()


class ConnectorHearbeat(models.Model):
    connector = models.ForeignKey(
        Connector, on_delete=models.CASCADE
    )
    last_heartbeat = models.DateTimeField()
    next_heartbeat = models.DateTimeField()


class ConnectorAvailableDatapoints(models.Model):
    connector = models.ForeignKey(
        Connector, on_delete=models.CASCADE
    )
    datapoint_type = models.CharField(max_length=8)
    datapoint_key_in_connector = models.TextField()
    datapoint_example_value = models.TextField()


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
