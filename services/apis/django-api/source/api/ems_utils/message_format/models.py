from django.db import models
from timescale.db.models.managers import TimescaleManager
from timescale.db.models.fields import TimescaleDateTimeField


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
    #   bool: A bool, i.e. only True or False.
    #   unknown: Unknown format. No checks applied.
    data_format_choices = [
        ("generic_numeric", "Generic Numeric"),
        ("continuous_numeric", "Continuous Numeric"),
        ("discrete_numeric", "Discrete Numeric"),
        ("generic_text", "Generic Text"),
        ("discrete_text", "Discrete Text"),
        ("bool", "Boolean"),
        ("unknown", "Unknown"),
    ]
    # Use generic_text as default as it imposes no constraints on the datapoint
    # apart from that the value can be stored as string, which should always
    # be possible as the value has been received as a JSON string.
    data_format = models.CharField(
        max_length=18,
        choices=data_format_choices,
        default="unknown",
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
    last_value = models.JSONField(
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


class TimescaleModel(models.Model):
    """
    A helper class for using Timescale within Django, has the TimescaleManager and
    TimescaleDateTimeField already present. This is an abstract class it should
    be inheritted by another class for use.
    """

    class Meta:
        abstract = True

    objects = models.Manager()
    timescale = TimescaleManager()

    time = TimescaleDateTimeField(
        interval="1 day",
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
    # TimescaleDB absolutely requires that the timestamp field is
    # called time. On the other hand a lot of code here expects that the
    # timestamp field is called timestamp. Hence this workaround.
    # def __getattribute__(self, attr):
    #     if attr == "timestamp":
    #         print("timestamp" % self.time)
    #         return self.time
    #     else:
    #         return super().__getattr__(attr)
    # def __setattr__(self, name, value):
    #     if name == "timestamp":
    #         self.time = value
    #     else:
    #         super().__setattr__(name, value)
    # @property
    # def timestamp(self):
    #     return self.time
    #
    # @timestamp.setter
    # def timestamp(self, value):
    #     self.time = value

    @staticmethod
    def bulk_update_or_create(model, msgs):
        """
        Create or update value/setpoint/schedule messages efficiently in bulks.

        This will not send any signals nor update the last_* values in
        datapoint. This seems not to be an issue as this function will likely
        be used only to restore backups.

        Arguments:
        ----------
        model : django Model
            The model for which the data should be written to.
        msgs : list of dict
            Each dict containting the fields (as keys) and desired values
            that should be stored for one object in the DB.

        Returns:
        --------
        msgs_created : int
            The number of messages that have been created.
        msgs_updated : int
            The number of messages that have been updated.
        """
        # Start with searching for msgs that exist already with the same
        # combination of timestamp and datapoint in the database.
        # These messages will be updated.
        msgs_by_datapoint = {}
        msgs_to_create = []
        msgs_updated = 0
        for msg in msgs:
            datapoint = msg["datapoint"]
            if datapoint not in msgs_by_datapoint:
                msgs_by_datapoint[datapoint] = []
            msgs_by_datapoint[datapoint].append(msg)
        for datapoint in msgs_by_datapoint:
            msgs_current_dp = msgs_by_datapoint[datapoint]
            msgs_c_dp_by_time = {msg["time"]: msg for msg in msgs_current_dp}
            existing_msg_objects = model.objects.filter(
                time__in=msgs_c_dp_by_time.keys()
            )

            # Now start with updating the existing messages by updating
            # the corresponding fields.
            fields_to_update = set()
            for existing_msg_object in existing_msg_objects:
                # The messages remaining in msgs_c_dp_by_time after the loop
                # are those we need to create.
                new_msg = msgs_c_dp_by_time.pop(existing_msg_object.time)
                for field in new_msg:
                    if field == "datapoint" or field == "time":
                        # These have been used to find the message and must thus
                        # not be updated.
                        continue
                    fields_to_update.add(field)
                    setattr(existing_msg_object, field, new_msg[field])

            # Without this if we will get an error like this downstream:
            # ValueError: Field names must be given to bulk_update().
            if existing_msg_objects:
                # Now let's push those updates back to DB. Use bulks of 1000
                # to prevent the SQL query from becoming too large. See:
                # https://docs.djangoproject.com/en/3.1/ref/models/querysets/#bulk-update
                model.objects.bulk_update(
                    objs=existing_msg_objects,
                    fields=fields_to_update,
                    batch_size=1000,
                )
                msgs_updated += len(existing_msg_objects)

            msgs_to_create.extend(msgs_c_dp_by_time.values())

        # Now that we have updated the existing messages and know which ones
        # are left to create let's to this too.
        objs_to_create = [model(**msg) for msg in msgs_to_create]
        model.objects.bulk_create(
            objs=objs_to_create,
            batch_size=1000,
        )
        msgs_created = len(objs_to_create)

        return msgs_created, msgs_updated


class DatapointValueTemplate(TimescaleModel):
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
                fields=['datapoint', 'time'],
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
    # JSON should be able to store everything as the messages arive
    # packed in a JSON string.
    value = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "The value part of the DatapointValue message."
        )
    )
    _value_float = models.FloatField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "Similar to value but an internal float representation "
            "to store numeric values more efficiently."
        )
    )
    _value_bool = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "Similar to value but an internal bool representation "
            "to store boolean values more efficiently."
        )
    )


    def save(self, *args, **kwargs):
        """
        Update the last_value/last_value_timestamp fields in datapoint too.
        Also check if the value can be stored as float or bool to save storage
        space.
        """
        # Store the value in the corresponding column.
        original_value = self.value
        if isinstance(self.value, bool):
            self._value_bool = self.value
            # PGSQL should be able to store the null rather efficiently.
            self.value = None
        elif self.value is not None:
            try:
                value_float = float(self.value)
                parsable = True
            except ValueError:
                parsable = False

            if parsable:
                self._value_float = value_float
                self.value = None
        super().save(*args, **kwargs)

        # Restore the original values, for any code that continous to work with
        # the object.
        self.value = original_value
        self._value_bool = None
        self._value_float = None

        # A message without a timestamp cannot be latest.
        if self.time is None:
            return

        self.datapoint.refresh_from_db()
        existing_ts = self.datapoint.last_value_timestamp

        if existing_ts is None or existing_ts <= self.time:
            self.datapoint.last_value = self.value
            self.datapoint.last_value_timestamp = self.time
            self.datapoint.save(
                update_fields=[
                    "last_value",
                    "last_value_timestamp",
                ]
            )

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        if instance._value_float is not None:
            instance.value = instance._value_float
            instance._value_float = None
        elif instance._value_bool is not None:
            instance.value = instance._value_bool
            instance._value_bool = None
        return instance

    @staticmethod
    def bulk_update_or_create(model, msgs):
        """
        Extend the version of TimescaleModel with special handling for the
        float and bool hidden fields.

        Arguments:
        ----------
        model : django Model
            The model for which the data should be written to.
        msgs : list of dict
            Each dict containting the fields (as keys) and desired values
            that should be stored for one object in the DB.

        Returns:
        --------
        msgs_created : int
            The number of messages that have been created.
        msgs_updated : int
            The number of messages that have been updated.
        """
        for msg in msgs:
            original_value = msg["value"]
            msg["value"] = None

            if isinstance(original_value, bool):
                msg["_value_bool"] = original_value
            elif original_value is not None:
                try:
                    msg["_value_float"] = float(original_value)
                except ValueError:
                    msg["value"] = original_value

        return TimescaleModel.bulk_update_or_create(model=model, msgs=msgs)


class DatapointScheduleTemplate(TimescaleModel):
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
                fields=['datapoint', 'time'],
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

    def save(self, *args, **kwargs):
        """
        Update the last_schedule/last_schedule_timestamp fields in datapoint
        too.
        """
        # But check first that the save for this object goes trough.
        super().save(*args, **kwargs)

        # A message without a timestamp cannot be latest.
        if self.time is None:
            return

        self.datapoint.refresh_from_db()
        existing_ts = self.datapoint.last_schedule_timestamp

        if existing_ts is None or existing_ts <= self.time:
            self.datapoint.last_schedule = self.schedule
            self.datapoint.last_schedule_timestamp = self.time
            self.datapoint.save(
                update_fields=[
                    "last_schedule",
                    "last_schedule_timestamp",
                ]
            )


class DatapointSetpointTemplate(TimescaleModel):
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
                fields=['datapoint', 'time'],
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

    def save(self, *args, **kwargs):
        """
        Update the last_setpoint/last_setpoint_timestamp fields in datapoint
        too.
        """
        # But check first that the save for this object goes trough.
        super().save(*args, **kwargs)

        # A message without a timestamp cannot be latest.
        if self.time is None:
            return

        self.datapoint.refresh_from_db()
        existing_ts = self.datapoint.last_setpoint_timestamp

        if existing_ts is None or existing_ts <= self.time:
            self.datapoint.last_setpoint = self.setpoint
            self.datapoint.last_setpoint_timestamp = self.time
            self.datapoint.save(
                update_fields=[
                    "last_setpoint",
                    "last_setpoint_timestamp",
                ]
            )
