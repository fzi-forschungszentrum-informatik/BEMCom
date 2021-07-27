from django.db import models


class DatapointTemplate(models.Model):
    """
    Devices are abstracted as a set of datapoints.

    A datapoint represents one source of information. Devices will typically
    emit information on more then one datapoints. E.g. climate sensor in a
    room might publish temperature and humidity measurements. Both will be
    treated as individual datapoints as this allows us to abstract away the
    complexity of the devices.

    Each datapoint object contains the metadata necessary to interpret
    the datapoint.
    """

    class Meta:
        abstract = True

    origin_id = models.TextField(
        null=True,
        unique=True,
        blank=True,
        help_text=(
            "This id used if the datapoint metadata is (partly) configured "
            "in an external service (e.g. BEMCom) and should be used in the "
            "curren service (e.g. the EMP). This field allows matching the "
            "ids of the external service with id maintained by the current "
            "service, which effectively allows the current service to use"
            "additional datapoints that do not exist in the external service, "
            "which is handy for mocking UIs and stuff."
        )
    )
    short_name = models.TextField(
        max_length=30,
        null=True,  # Auto generated datapoints will be stored as null.
        default=None,
        unique=True,
        # Allowing short name to be an empty string would raise unique
        # validation errors. So we ensure while saving the model that
        # empty strings will be stored as Nones. However, we still need
        # to allow blank inputs to prevent validation errors in admin.
        blank=True,
        help_text=(
            "A short name to identify the datapoint."
        )
    )
    TYPE_CHOICES = [
        ("sensor", "Sensor"),
        ("actuator", "Actuator"),
    ]
    type = models.CharField(
        max_length=8,
        default=None,
        null=False,
        choices=TYPE_CHOICES,
        help_text=(
            "Datapoint type, can be ether sensor or actuator."
        )
    )
    # Defines the data format of the datapoint, i.e. which additional metadata
    # we can expect to have reasonable values.
    #
    # The formats have the following meanings:
    #   numeric: The value of the datapoint can be stored as a float.
    #   text: The value of the datapoint can be stored as a string.
    #   generic: No additional information.
    #   continuous: The value is a continuous variable with an optional max
    #               and min value, that can take any value in between.
    #   discrete: The value of the datapoint can take one value of limited set
    #             of possible values.
    data_format_choices = [
        ("generic_numeric", "Generic Numeric"),
        ("continuous_numeric", "Continuous Numeric"),
        ("discrete_numeric", "Discrete Numeric"),
        ("generic_text", "Generic Text"),
        ("discrete_text", "Discrete Text"),
    ]
    # Use generic_text as default as it imposes no constraints on the datapoint
    # apart from that the value can be stored as string, which should always
    # be possible as the value has been received as a JSON string.
    data_format = models.CharField(
        max_length=18,
        choices=data_format_choices,
        default="generic_text",
        help_text=(
            "Format of the datapoint value. Additionally defines which meta"
            "data is available for it. See documentation in code for details."
        )
    )
    # Don't limit this, people should never need to use abbreviations or
    # shorten their thoughts just b/c the field is too short.
    description = models.TextField(
        editable=True,
        blank=True,
        help_text=(
            "A human readable description of the datapoint targeted on "
            "users of the API wihtout knowledge about connector details."
        )
    )
    #
    ##########################################################################
    #
    # Below all metadata fields that may or may not be populated for a
    # particular datapoint depending on the data_format and type.
    #
    ##########################################################################
    #
    allowed_values = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "Allowed values. Applicable to discrete valued datapoints. "
            "Must be a valid JSON string."
        )
    )
    min_value = models.FloatField(
        blank=True,
        null=True,
        default=None,
        help_text=(
            "The minimal expected value of the datapoint. "
            "Applicable to numeric datapoints."
        )
    )
    max_value = models.FloatField(
        blank=True,
        null=True,
        default=None,
        help_text=(
            "The maximal expected value of the datapoint. "
            "Applicable to numeric datapoints."
        )
    )
    unit = models.TextField(
        editable=True,
        default="",
        blank=True,
        help_text=(
            "The unit in SI notation, e.g.  Mg*m*s^-2 aka. kN. "
            "Applicable to numeric datapoints."
        )
    )
    #
    ##########################################################################
    #
    # Store the last value and timestamp for each message type as these are
    # frequently accessed and we can save a hell lot of DB lockups if we
    # store them in the datapoint too.
    #
    ##########################################################################
    #
    last_value = models.TextField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "The last value received for the datapoint. We store all values "
            "including numeric as strings as this simplfies the logic "
            "significantly and prevents unintended side effects, e.g. data "
            "loss if the data format field is changed."
            ""
        )
    )
    last_value_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "The timestamp of the last value received via MQTT."
        )
    )
    last_setpoint = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "The last schedule received for the datapoint. "
            "Applicable to actuator datapoints."
        )
    )
    last_setpoint_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "The timestamp of the last value received for the datapoint."
            "Applicable to actuator datapoints."
        )
    )
    last_schedule = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "The last schedule received for the datapoint."
            "Applicable to actuator datapoints."
        )
    )
    last_schedule_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "The timestamp of the last value received for the datapoint."
            "Applicable to actuator datapoints."
        )
    )

    def save(self, *args, **kwargs):
        """
        Replace an empty string in origin_id with None (which cannot be
        entered directly in the admin), as every None is unique while
        an empty string violates the unique constraint. However, we want
        external id only to be unique if it is set.
        """
        if self.origin_id == "":
            self.origin_id = None
        if self.short_name == "":
            self.short_name = None
        super().save(*args, **kwargs)

    def __str__(self):
        if self.short_name is not None:
            return (str(self.id) + " - " + self.short_name)
        else:
            return str(self.id)


class DatapointValueTemplate(models.Model):
    """
    Represents a value of a Datapoint.

    For a sensor datapoint: Represents a measurement emitted by a device.
    Message is published by the corresponding connector service.

    For an actuator datapoint: Represents a set value that should be
    "written" to an device actuator. Message is created by an external
    entity, send to the API service which publishes the message on the
    broker.
    """

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=['datapoint', 'timestamp'],
                name='Value msg unique for timestamp',
            ),
        ]


    datapoint = models.ForeignKey(
        DatapointTemplate,
        on_delete=models.CASCADE,
        help_text=(
            "The datapoint that the value message belongs to."
        )
    )
    value = models.TextField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "The last value of the datapoint. Will be a string "
            "or null. Values of numeric datapoints are sent "
            "as strings too, as this drastically reduces effort "
            "for implementing the REST interfaces."
        )
    )
    value_float = models.FloatField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "Similar to value but an internal float representation for "
            "numeric datapoints."
        )
    )

    timestamp = models.DateTimeField(
        null=False,
        blank=False,
        default=None,
        help_text=(
            "For sensor datapoints: The time the value was "
            "received by the connector.\n"
            "For actuator datapoints: The time the message was "
            "created by the external entity.\n"
            "Both in milliseconds since 1970-01-01 UTC."
        )
    )

    def save(self, *args, **kwargs):
        """
        Update the last_value/last_value_timestamp fields in datapoint too.
        """
        # Check if we can store the value as float, which is probably
        # much more storage effiecient, comparing at least one byte
        original_value = self.value
        if self.value is not None:
            try:
                value_float = float(self.value)
                parsable = True
            except ValueError:
                parsable = False

            if parsable:
                self.value_float = value_float
                # AFAIK, null values can be stored quite effieciently by
                # most databases.
                self.value = None

        super().save(*args, **kwargs)

        # Restore the original value, for any code that continous to work with
        # the object.
        self.value = original_value

        # A message without a timestamp cannot be latest.
        if self.timestamp is None:
            return

        self.datapoint.refresh_from_db()
        existing_ts = self.datapoint.last_value_timestamp

        if existing_ts is None or existing_ts <= self.timestamp:
            print(original_value)
            self.datapoint.last_value = self.value
            self.datapoint.last_value_timestamp = self.timestamp
            self.datapoint.save(
                update_fields=[
                    "last_value",
                    "last_value_timestamp",
                ]
            )

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        if instance.value_float is not None:
            instance.value = str(instance.value_float)
        return instance


class DatapointScheduleTemplate(models.Model):
    """
    The schedule is a list of actuator values computed by an optimization
    algorithm that should be executed on the specified actuator datapoint
    as long as the setpoint constraints are not violated. Executing
    setpoints requires a controller service in BEMCom.
    """

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=['datapoint', 'timestamp'],
                name='Schedule msg unique for timestamp',
            ),
        ]

    datapoint = models.ForeignKey(
        DatapointTemplate,
        on_delete=models.CASCADE,
        help_text=(
            "The datapoint that the schedule message belongs to."
        )
    )
    schedule = models.JSONField(
        null=False,
        blank=True,
        default=list,
        help_text=(
            "A JSON array holding zero or more DatapointScheduleItems."
        )
    )
    timestamp = models.DateTimeField(
        null=False,
        blank=False,
        default=None,
        help_text=(
            "The time the message was created by the external entity in "
            "milliseconds since 1970-01-01 UTC."
        )
    )

    def save(self, *args, **kwargs):
        """
        Update the last_schedule/last_schedule_timestamp fields in datapoint
        too.
        """
        # But check first that the save for this object goes trough.
        super().save(*args, **kwargs)

        # A message without a timestamp cannot be latest.
        if self.timestamp is None:
            return

        self.datapoint.refresh_from_db()
        existing_ts = self.datapoint.last_schedule_timestamp

        if existing_ts is None or existing_ts <= self.timestamp:
            self.datapoint.last_schedule = self.schedule
            self.datapoint.last_schedule_timestamp = self.timestamp
            self.datapoint.save(
                update_fields=[
                    "last_schedule",
                    "last_schedule_timestamp",
                ]
            )


class DatapointSetpointTemplate(models.Model):
    """
    The setpoint specifies the demand of the users of the system. The setpoint
    must hold a preferred_value which is the value the user would appreciate
    most, and can additionally define flexibility of values the user would also
    accept. The setpoint message is used by optimization algorithms as
    constraints while computing schedules, as well as by controller services
    to ensure that the demand of the user is always met.
    """

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=['datapoint', 'timestamp'],
                name='Setpoint msg unique for timestamp',
            ),
        ]

    datapoint = models.ForeignKey(
        DatapointTemplate,
        on_delete=models.CASCADE,
        help_text=(
            "The datapoint that the setpoint message belongs to."
        )
    )
    setpoint = models.JSONField(
        null=False,
        blank=True,
        default=list,
        help_text=(
            "A JSON array holding zero or more DatapointSetpointItems."
        )
    )
    timestamp = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "The time the message was created by the external entity in "
            "milliseconds since 1970-01-01 UTC."
        )
    )

    def save(self, *args, **kwargs):
        """
        Update the last_setpoint/last_setpoint_timestamp fields in datapoint
        too.
        """
        # But check first that the save for this object goes trough.
        super().save(*args, **kwargs)

        # A message without a timestamp cannot be latest.
        if self.timestamp is None:
            return

        self.datapoint.refresh_from_db()
        existing_ts = self.datapoint.last_setpoint_timestamp

        if existing_ts is None or existing_ts <= self.timestamp:
            self.datapoint.last_setpoint = self.setpoint
            self.datapoint.last_setpoint_timestamp = self.timestamp
            self.datapoint.save(
                update_fields=[
                    "last_setpoint",
                    "last_setpoint_timestamp",
                ]
            )
