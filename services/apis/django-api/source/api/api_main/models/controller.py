"""
This model contains all the data that is necessary for configuring the
controller services. (That can be multiple in theory).
"""
from django.db import models

from .datapoint import Datapoint


class Controller(models.Model):
    """
    Model for the Controller, similar to the connector model.

    This defines all Configuration data about the Controller itself that is
    required to connect it, that is mostly the correct topic for
    configuration.
    """

    name = models.TextField(
        blank=False,
        default=None,
        unique=True,
        verbose_name="Controller name, used for display in the admin page.",
    )
    mqtt_topic_controlled_datapoints = models.TextField(
        blank=False,
        default=None,
        editable=True,
        unique=True,
        verbose_name=(
            "MQTT topic on which the controller awaits the configuration data."
        ),
    )

    def __str__(self):
        return self.name


class ControlledDatapoint(models.Model):
    """
    Model for one entry in the configuration data for the controller.

    This essentially maps a sensor datapoint to an actuator datapoint.
    """

    controller = models.ForeignKey(
        Controller, on_delete=models.CASCADE, editable=True
    )
    sensor_datapoint = models.ForeignKey(
        Datapoint,
        on_delete=models.CASCADE,
        editable=True,
        related_name="controller_sensor_datapoint",
    )
    actuator_datapoint = models.ForeignKey(
        Datapoint,
        on_delete=models.CASCADE,
        editable=True,
        related_name="controller_actuator_datapoint",
    )
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Flag if the this mapping should currently be used (i.e. be "
            "published as part of the controlled_datapoints msg to the "
            "controller)."
        ),
    )
