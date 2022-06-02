#!/usr/bin/env python3
"""
The django models corresponding to esg.models.metadata.
"""
from django.db import models

from esg.django_models.base import DjangoBaseModel
from esg.models.metadata import GeographicPosition
from esg.models.metadata import PVSystem
from esg.models.metadata import Plant
from esg.models.metadata import Product
from esg.models.metadata import ProductRun
from esg.services.base import RequestInducedException


class ProductTemplate(DjangoBaseModel):
    """
    Intended model to store "esg.models.metadata.Product" objects.

    Subclass to use. Ensure to that the relation stays `ManyToMany`.
    """

    class Meta:
        abstract = True

    pydantic_model = Product

    name = models.TextField(
        blank=pydantic_model.__fields__["name"].allow_none,
        null=pydantic_model.__fields__["name"].allow_none,
        # Name must be unique as we use the name to select plants belonging
        # to a product by name.
        unique=True,
        help_text=pydantic_model.__fields__["name"].field_info.description,
    )
    service_url = models.TextField(
        blank=pydantic_model.__fields__["service_url"].allow_none,
        null=pydantic_model.__fields__["service_url"].allow_none,
        help_text=pydantic_model.__fields__[
            "service_url"
        ].field_info.description,
    )
    coverage_from = models.DurationField(
        blank=pydantic_model.__fields__["coverage_from"].allow_none,
        null=pydantic_model.__fields__["coverage_from"].allow_none,
        help_text=pydantic_model.__fields__[
            "coverage_from"
        ].field_info.description,
    )
    coverage_to = models.DurationField(
        blank=pydantic_model.__fields__["coverage_to"].allow_none,
        null=pydantic_model.__fields__["coverage_to"].allow_none,
        help_text=pydantic_model.__fields__[
            "coverage_to"
        ].field_info.description,
    )

    def __str__(self):
        if self.name is not None:
            return str(self.id) + " - " + self.name
        else:
            return str(self.id)


class PlantTemplate(DjangoBaseModel):
    """
    Intended model to store "esg.models.metadata.Plant" objects.

    Subclass to use. Take care to take over the `OneToOneField` as it ensures
    that a plant can have at most one position etc.
    """

    class Meta:
        abstract = True

    pydantic_model = Plant

    name = models.TextField(
        blank=Plant.__fields__["name"].allow_none,
        null=Plant.__fields__["name"].allow_none,
        help_text=Plant.__fields__["name"].field_info.description,
    )

    products = models.ManyToManyField(ProductTemplate, related_name="plants")

    def __str__(self):
        if self.name is not None:
            return str(self.id) + " - " + self.name
        else:
            return str(self.id)

    @property
    def geographic_position(self):
        value = self.load_dict_from_related_obj("_geographic_position")
        return value

    @geographic_position.setter
    def geographic_position(self, value):
        self.store_pydantic_instance_in_related_obj(
            related_name="_geographic_position",
            field_name_parent_reference="plant",
            pydantic_instance=value,
        )

    @property
    def pv_system(self):
        value = self.load_dict_from_related_obj("_pv_system")
        return value

    @pv_system.setter
    def pv_system(self, value):
        self.store_pydantic_instance_in_related_obj(
            related_name="_pv_system",
            field_name_parent_reference="plant",
            pydantic_instance=value,
        )

    @property
    def product_ids(self):
        # ManyToMany relationships can only be used after the ID is set,
        # however, `clean()` will request this field before we save for the
        # first time.
        if self.id is None:
            return []

        # Once the relationship can be used, just return the names.
        value = [s[0] for s in self.products.values_list("id")]
        return value

    @product_ids.setter
    def product_ids(self, value):
        if value:
            related_model = self.products.model
            for product_id in value:
                try:
                    product = related_model.objects.get(id=product_id)
                except related_model.DoesNotExist:
                    # This Exception is request related and does usually
                    # not belong in the model. However, it is much simpler
                    # to raise here, then to reconstruct the reason later.
                    raise RequestInducedException(
                        detail=(
                            "Cannot link plant to product `{}`, no product "
                            "with such id.".format(product_id)
                        )
                    )
                self.products.add(product)


class GeographicPositionTemplate(DjangoBaseModel):
    """
    Intended model to store "esg.models.metadata.GeographicPosition" objects.

    Subclass to use. Ensure to that the relation stays a `OneToOne` and that
    `related_name` is kept at this value as this is expected by `Plant`.
    """

    class Meta:
        abstract = True

    pydantic_model = GeographicPosition

    plant = models.OneToOneField(
        PlantTemplate,
        on_delete=models.CASCADE,
        related_name="_geographic_position",
    )
    latitude = models.FloatField(
        blank=pydantic_model.__fields__["latitude"].allow_none,
        null=pydantic_model.__fields__["latitude"].allow_none,
        help_text=pydantic_model.__fields__["latitude"].field_info.description,
    )
    longitude = models.FloatField(
        blank=pydantic_model.__fields__["longitude"].allow_none,
        null=pydantic_model.__fields__["longitude"].allow_none,
        help_text=pydantic_model.__fields__["longitude"].field_info.description,
    )
    height = models.FloatField(
        blank=pydantic_model.__fields__["height"].allow_none,
        null=pydantic_model.__fields__["height"].allow_none,
        help_text=pydantic_model.__fields__["height"].field_info.description,
    )


class PVSystemTemplate(DjangoBaseModel):
    """
    Intended model to store "esg.models.metadata.PVSystem" objects.

    Subclass to use. Ensure to that the relation stays a `OneToOne` and that
    `related_name` is kept at this value as this is expected by `Plant`.
    """

    class Meta:
        abstract = True

    pydantic_model = PVSystem

    plant = models.OneToOneField(
        PlantTemplate, on_delete=models.CASCADE, related_name="_pv_system",
    )
    # GOTCHA: This should actually be `DatapointTemplate` not `PlantTemplate`
    #         However, this would result in a circular import error. Hence
    #         here this quick solution as this field must be overloaded any
    #         way.
    _power_datapoint = models.OneToOneField(
        PlantTemplate,
        on_delete=models.CASCADE,
        # Note this must be nullable to allow saving with a new instance
        # with `esg.django_models.base.DjangoBaseModel.save_from_pydantic()`
        null=True,
        related_name="_pv_system",
    )
    azimuth_angle = models.FloatField(
        blank=pydantic_model.__fields__["azimuth_angle"].allow_none,
        null=pydantic_model.__fields__["azimuth_angle"].allow_none,
        help_text=pydantic_model.__fields__[
            "azimuth_angle"
        ].field_info.description,
    )
    inclination_angle = models.FloatField(
        blank=pydantic_model.__fields__["inclination_angle"].allow_none,
        null=pydantic_model.__fields__["inclination_angle"].allow_none,
        help_text=pydantic_model.__fields__[
            "inclination_angle"
        ].field_info.description,
    )
    nominal_power = models.FloatField(
        blank=pydantic_model.__fields__["nominal_power"].allow_none,
        null=pydantic_model.__fields__["nominal_power"].allow_none,
        help_text=pydantic_model.__fields__[
            "nominal_power"
        ].field_info.description,
    )

    @property
    def power_datapoint_id(self):
        if self._power_datapoint is not None:
            return self._power_datapoint.id
        else:
            return None

    # NOTE: You must copy paste this too.
    #       Replace `PlantTemplate` with `Datapoint`
    @power_datapoint_id.setter
    def power_datapoint_id(self, value):
        try:
            datapoint = PlantTemplate.objects.get(id=value)
        except PlantTemplate.DoesNotExist:
            # This Exception is request related and does usually
            # not belong in the model. However, it is much simpler
            # to raise here, then to reconstruct the reason later.
            raise RequestInducedException(
                detail=(
                    "Cannot link pv_system to datapoint `{}`, no datapoint "
                    "with such id.".format(value)
                )
            )
        self._power_datapoint = datapoint


class ProductRunTemplate(DjangoBaseModel):
    """
    Intended model to store "esg.models.metadata.ProductRun" objects.

    Subclass to use. Copy and modify the ForeignKey field as well as
    all two properties.
    """

    class Meta:
        abstract = True

    pydantic_model = ProductRun

    _product = models.ForeignKey(
        ProductTemplate,
        on_delete=models.CASCADE,
        # Must allow null as field will be null for a short time
        # during saving with `save_from_pydantic`
        null=True,
        related_name="product_runs",
    )
    plants = models.ManyToManyField(PlantTemplate, related_name="product_runs")
    available_at = models.DateTimeField(
        blank=pydantic_model.__fields__["available_at"].allow_none,
        null=pydantic_model.__fields__["available_at"].allow_none,
        help_text=pydantic_model.__fields__[
            "available_at"
        ].field_info.description,
    )
    coverage_from = models.DateTimeField(
        blank=pydantic_model.__fields__["coverage_from"].allow_none,
        null=pydantic_model.__fields__["coverage_from"].allow_none,
        help_text=pydantic_model.__fields__[
            "coverage_from"
        ].field_info.description,
    )
    coverage_to = models.DateTimeField(
        blank=pydantic_model.__fields__["coverage_to"].allow_none,
        null=pydantic_model.__fields__["coverage_to"].allow_none,
        help_text=pydantic_model.__fields__[
            "coverage_to"
        ].field_info.description,
    )

    @property
    def product_id(self):
        return self.get_fk_id_from_field(self._product)

    @product_id.setter
    def product_id(self, value):
        self._product = self.set_fk_obj_by_id(value, ProductTemplate)

    @property
    def plant_ids(self):
        # ManyToMany relationships can only be used after the ID is set,
        # however, `clean()` will request this field before we save for the
        # first time.
        if self.id is None:
            return []

        # Once the relationship can be used, just return the names.
        value = [s[0] for s in self.plants.values_list("id")]
        return value

    @plant_ids.setter
    def plant_ids(self, value):
        if value:
            related_model = self.plants.model
            for plant_id in value:
                try:
                    plant = related_model.objects.get(id=plant_id)
                except related_model.DoesNotExist:
                    # This Exception is request related and does usually
                    # not belong in the model. However, it is much simpler
                    # to raise here, then to reconstruct the reason later.
                    raise RequestInducedException(
                        detail=(
                            "Cannot link product run to plant `{}`, no plant "
                            "with such id.".format(plant_id)
                        )
                    )
                self.plants.add(plant)

    def __str__(self):
        if self.available_at is not None:
            corresponding_time = self.available_at
        else:
            corresponding_time = self.started_at
        return str(corresponding_time)
