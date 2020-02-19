from django.db import models
from django.utils.text import slugify
from django.contrib.contenttypes.models import ContentType

from .connector import Connector


class Datapoint(models.Model):
    """
    Model for a datapoint.

    This model holds the generic information of a datapoint, i.e. the data
    that should be set for every datapoint regardless of which information it
    represents. By default a datapoint can ether hold a numeric information
    (e.g. 2.0912) or a text information (e.g. "OK").

    Depeding on the use case, the datapoint may require (or should be able to
    carry) additional metadata fields. If you encounter Datapoints that require
    other metadata then is defined in DatapointAddition models below, simply
    generate a new DatapointAddition model and extend `data_format_choices`
    and `data_format_addition_models` accordingly.

    TODO: May be replace delete with deactivate, else we will might end with
          entries in the ValueDB with unknown origin (deleted datapoints will
          be rentered but with new id)
    """

    connector = models.ForeignKey(
        Connector,
        on_delete=models.CASCADE,
        editable=False,
    )
    is_active = models.BooleanField(
        default=False,
        help_text=(
            "Flag if the connector should publish values for this datapoint."
        )
    )
    is_accessible = models.BooleanField(
        default=False,
        help_text=(
            "Flag if the datapoint is accessible via the API."
        )
    )
    # This must be unlimeted to prevent errors from cut away keys while
    # using the datapoint map by the connector.
    key_in_connector = models.TextField(
        editable=False,
        help_text=(
            "Internal key used by the connector to identify the datapoint "
            "in the incoming/outgoing data streams."
        )
    )
    type = models.CharField(
        max_length=8,
        editable=False,
        default=None,
        help_text=(
            "Datapoint type, can be ether sensor or actuator. Is defined by "
            "the connector."
        )
    )
    # Defines the data format of the datapoint, i.e. the additional metadata
    # fields. The 'actual value' (i.e. the first element of the tuple) must
    # match the key in data_format_addition_models.
    #
    # The formats have the following meanings:
    #   numeric: The value of the datapoint can be stored as a float.
    #   text: The value of the datapoint can be stored as a string.
    #   generic: No additional information.
    #   continuous: The value is a continuous variable with an optional max
    #               and min value, that can take any value in between.
    #   discrete: The value of the datapoint can take one value of limited set
    #             of possible values.
    #
    # Be very careful to not change the "generic" string, it's expected
    # exactly like this in a lot of places.
    data_format_choices = [
        ("generic_numeric", "Generic Numeric"),
        ("continuous_numeric", "Continuous Numeric"),
        ("discrete_numeric", "Discrete Numeric"),
        ("generic_text", "Generic Text"),
        ("discrete_text", "Discrete Text"),
    ]
    # Mapping to which model to use for the addtional metadata fields.
    # The value must be a dict of valid kwargs expected by
    # django.contrib.contenttypes.models.ContentType.objects.get()
    #
    # Gotcha: The model name must be all lowercase not as in the class name.
    #
    # Compute the app_label from the inherited `_meta` attribute of a temporary
    # class. This seems hacky, but we cannot access Datapoint at this point as
    # it is not fully defined yet,and the addition models must follow below
    # as they reference Datapoint. Computing app_label however allows us to use
    # the Datapoint model in several django apps.

    class TempModel(models.Model):
        pass
    app_label = TempModel._meta.app_label
    data_format_addition_models = {
        "generic_numeric": {
            "app_label": app_label,
            "model": "genericnumericdatapointaddition",
        },
        "continuous_numeric": {
            "app_label": app_label,
            "model": "continuousnumericdatapointaddition",
        },
        "discrete_numeric": {
            "app_label": app_label,
            "model": "discretenumericdatapointaddition",
        },
        "generic_text": {
            "app_label": app_label,
            "model": "generictextdatapointaddition",
        },
        "discrete_text": {
            "app_label": app_label,
            "model": "discretetextdatapointaddition",
        },
    }
    # Use generic_text as default as it imposes no constraints on the datapoint
    # apart from that the value can be stored as string, which should always
    # be possible as the value has been received as a JSON string.
    data_format = models.CharField(
        max_length=18,
        choices=data_format_choices,
        default="generic_text",
        help_text=(
            "Format of the datapoint value. Additionally defines which meta"
            "data is available for it. See documentation for details."
        )
    )
    example_value = models.CharField(
        max_length=30,
        editable=False,
        help_text=(
            "One example value for this datapoint. Should help admins while "
            "mangeing datapoints, i.e. to specify the correct data format."
        )
    )
    # Don't limit this, people should never need to use abbreviations or
    # shorten their thoughts just b/c the field is too short.
    description = models.TextField(
        editable=True,
        help_text=(
            "A human readable description of the datapoint targeted on "
            "users of the API wihtout knowledge about connector details."
        )
    )

    def __str__(self):
        return slugify(self.key_in_connector)

    def save(self, *args, **kwargs):
        """
        Handle the potentially changed usage value, and manage (i.e.
        create/delete) the respective objects in the addition models.

        TODO: Write default value for description.
        TODO: Adept to changed fields.
        """

        # New instance, create a new object for the respective
        # Addition. Assume that until now no such object in of the
        # addition models exists.
        if not self.id:
            # At first trigger a save of self, this is required that we can
            # use it as a relation.
            super(Datapoint, self).save(*args, **kwargs)

            # This is False for "not used" and potentially an other
            # datapoint usage pattern that requires no additional metadata.
            try:
                if self.use_as in self.use_as_addition_models:
                    ct_kwargs = self.use_as_addition_models[self.use_as]
                    addition_type = ContentType.objects.get(**ct_kwargs)
                    addition_model = addition_type.model_class()
                    addition_model(
                        datapoint=self,
                    ).save()
            except Exception:
                # Undo save if the creation of the addition object failed to
                # prevent inconsistent states in DB.
                Datapoint.objects.get(id=self.id).delete()
                raise
            return

        #
        # Below here only for Existing datapoint instance.
        #
        # Check if use_as has changed and trigger a normal save if not.
        use_as_as_in_db = Datapoint.objects.get(id=self.id).use_as
        if use_as_as_in_db == self.use_as:
            super(Datapoint, self).save(*args, **kwargs)
            return

        # Now we now that use_as has chaged, delete the object for the old
        # datapoint addition (if the if statement below is true there should
        # exist one and only one entry in the respective model, as it should
        # have been created by the last run of this method)
        if use_as_as_in_db in self.use_as_addition_models:
            ct_kwargs = self.use_as_addition_models[use_as_as_in_db]
            addition_type = ContentType.objects.get(**ct_kwargs)
            addition_model = addition_type.model_class()
            # DatapointAddition should use a OneToOne relation, hence there
            # should be onyl one entry for this query.
            addition_model.objects.get(datapoint=self.id).delete()

        # Finally create the new datapoint addition entry if applicable.
        if self.use_as in self.use_as_addition_models:
            ct_kwargs = self.use_as_addition_models[self.use_as]
            addition_type = ContentType.objects.get(**ct_kwargs)
            addition_model = addition_type.model_class()
            addition_model(
                datapoint=self,
            ).save()

        super(Datapoint, self).save(*args, **kwargs)

    def get_mqtt_topic(self):
        """
        Computes the MQTT topic of the datapoint.

        This uses the mqtt_topic_wildcard part of the connector and adds the
        primary key of the Datapoint table. The later alows efficent mapping
        of incoming messages to Datapoint objects.

        Returns:
        --------
        mqtt_topic: str
            A string with the mqtt_topic of the datapoint.
        """
        # Removes the trailing wildcard `#`
        prefix = self.connector.mqtt_topic_datapoint_message_wildcard[:-1]
        return prefix + str(self.id)

    def get_addition_model(self,  use_as=None):
        """
        A convenient shorthand to return the model of a Datapoint Additon.

        Arguements:
        -----------
        use_as: string or None
            The `use_as` value to compute the corresponding DatapointAddition.
            If None will use the `use_as` value of self.

        Returns:
        --------
        addition_model: django.db.models.Model or None
            The corresponding DatapointAddition model if existing for `use_as`.
            Will be None if no such model exists.
        """
        if use_as is None:
            use_as = self.use_as

        if use_as not in self.use_as_addition_models:
            addition_model = None
        else:
            ct_kwargs = self.use_as_addition_models[use_as]
            addition_type = ContentType.objects.get(**ct_kwargs)
            addition_model = addition_type.model_class()
        return addition_model

    def get_addition_object(self):
        """
        A shorthand to return the DatapointAddition object for the Datapoint.

        Returns:
        --------
        addition_object: DatapointAddition.object or None
            Returns None if not additon object exists (e.g. use_as="not_used").
            Else returns the object.
        """
        addition_model = self.get_addition_model()
        if addition_model is None:
            addition_object = None
        else:
            # This is possible as `datapoint` of the AdditionModel is set to be
            # a OneToOneField with `primary_key` = True
            addition_object = addition_model.objects.get(datapoint_id=self.id)
        return addition_object


class TextDatapointAddition(models.Model):
    """
    This extends the Datapoint model with metadata specific for text
    datapoints.
    """

    # The metadata belongs to exactly one datapoint.
    datapoint = models.OneToOneField(
        Datapoint,
        on_delete=models.CASCADE,
        primary_key=True,
        editable=False,
    )
    last_value = models.TextField(
        editable=False,
        null=True,
        help_text=(
            "The last value received via MQTT."
        )
    )
    last_timestamp = models.DateTimeField(
        editable=False,
        null=True,
        help_text=(
            "The timestamp of the last value received via MQTT."
        )
    )


#class DatapointUnit(models.Model):
#
#    def __str__(self):
#        return self.unit_quantity + " [" + self.unit_symbol + "]"
#
#    unit_quantity = models.TextField(
#        help_text="The quantity of the unit, e.g. Temperature or Power"
#    )
#    unit_symbol = models.TextField(
#        help_text="The short symbol of the unit, e.g. °C or kW"
#    )

# TODO Update Datapoint Addition models.

class NumericDatapointAddition(models.Model):
    """
    This extends the Datapoint model with metadata specific for numeric
    datapoints.

    TODO: Define abstract base class DatapointAddition.
    """

    # The metadata belongs to exactly one datapoint.
    datapoint = models.OneToOneField(
        Datapoint,
        on_delete=models.CASCADE,
        primary_key=True,
        editable=False,
    )
    last_value = models.FloatField(
        editable=False,
        null=True,
        help_text=(
            "The last value received via MQTT."
        )
    )
    last_timestamp = models.DateTimeField(
        editable=False,
        null=True,
        help_text=(
            "The timestamp of the last value received via MQTT."
        )
    )
#    unit = models.ForeignKey(
#        DatapointUnit,
#        on_delete=models.SET('')
#    )
    min_value = models.FloatField(
        blank=True,
        null=True,
        default=None,
        help_text=(
            "The minimal expected value of the datapoint. Is uesed for "
            "automatically scaling plots."
        )
    )
    max_value = models.FloatField(
        blank=True,
        null=True,
        default=None,
        help_text=(
            "The maximal expected value of the datapoint. Is uesed for "
            "automatically scaling plots."
        )
    )
