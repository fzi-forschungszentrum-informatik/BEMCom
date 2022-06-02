#!/usr/bin/env python3
"""
"""
from copy import deepcopy
from datetime import timedelta
import pytest

from esg.test import data as td

try:
    from django.db import models

    from esg.test.django import GenericDjangoModelTemplateTest
    from esg.test.django import GenericDjangoModelTestMixin

    django_unavailable = False
except ModuleNotFoundError:

    class GenericDjangoModelTemplateTest:
        pass

    class GenericDjangoModelTestMixin:
        pass

    django_unavailable = True


@pytest.mark.skipif(django_unavailable, reason="requires django")
class TestProduct(GenericDjangoModelTemplateTest, GenericDjangoModelTestMixin):

    model_name = "Product"
    msgs_as_python = [m["Python"] for m in td.products]
    msgs_as_jsonable = [m["JSONable"] for m in td.products]
    invalid_msgs_as_python = [m["Python"] for m in td.invalid_products]

    @classmethod
    def define_models(cls):
        from esg.django_models.metadata import ProductTemplate

        class Product(ProductTemplate):
            """
            Create instance of model template.
            """

            class Meta:
                app_label = cls.__name__

        return [Product]

    def prepare_messages(self, msgs, msg_name):
        """
        Add an ID to the expected data as the DB adds one automatically.
        """
        if msg_name in ["msgs_as_jsonable"]:
            msgs = deepcopy(msgs)
            for i, msg in enumerate(msgs):
                if msg["id"] is None:
                    msg["id"] = i + 1
        return msgs


@pytest.mark.skipif(django_unavailable, reason="requires django")
class TestPlant(GenericDjangoModelTemplateTest, GenericDjangoModelTestMixin):
    """
    Note: This test cannot verify any data that reads/writes data from the
    `product_ids` property, due to some bug that is likely related to
    the way django handles related fields and our approach here to test
    temporary models. If you work on the `product_name` make sure it works
    afterwards by checking in a the EMP.
    """

    model_name = "Plant"
    msgs_as_python = [m["Python"] for m in td.plants]
    msgs_as_jsonable = [m["JSONable"] for m in td.plants]
    invalid_msgs_as_python = [m["Python"] for m in td.invalid_plants]

    @classmethod
    def define_models(cls):
        from esg.django_models.metadata import ProductTemplate
        from esg.django_models.metadata import PlantTemplate
        from esg.django_models.metadata import GeographicPositionTemplate
        from esg.django_models.metadata import PVSystemTemplate

        class Product(ProductTemplate):
            """
            Create instance of model template.
            """

            class Meta:
                app_label = cls.__name__

        class Plant(PlantTemplate):
            class Meta:
                app_label = cls.__name__

            products = models.ManyToManyField(Product, related_name="plants")

            @property
            def product_ids(self):
                return []

            @product_ids.setter
            def product_ids(self, value):
                pass

        class GeographicPosition(GeographicPositionTemplate):
            class Meta:
                app_label = cls.__name__

            plant = models.OneToOneField(
                Plant,
                on_delete=models.CASCADE,
                related_name="_geographic_position",
            )

        class PVSystem(PVSystemTemplate):
            class Meta:
                app_label = cls.__name__

            plant = models.OneToOneField(
                Plant, on_delete=models.CASCADE, related_name="_pv_system",
            )
            # Ignore power_datapoint attribute. Testing it seems super hard.
            power_datapoint_id = None
            _power_datapoint = None

        Plant._related_name_to_model = {
            "_geographic_position": GeographicPosition,
            "_pv_system": PVSystem,
        }

        return [Product, Plant, GeographicPosition, PVSystem]

    def prepare_messages(self, msgs, msg_name):
        """
        Add an ID to the expected data as the DB adds one automatically.
        """
        if msg_name in ["msgs_as_jsonable"]:
            msgs = deepcopy(msgs)
            for i, msg in enumerate(msgs):
                if msg["id"] is None:
                    msg["id"] = i + 1
                # Make the expectation matching the (hopefully only in test)
                # returned value.
                msg["product_ids"] = []
        return msgs


@pytest.mark.skipif(django_unavailable, reason="requires django")
class TestGeographicPosition(
    GenericDjangoModelTemplateTest, GenericDjangoModelTestMixin
):

    model_name = "GeographicPosition"
    msgs_as_python = [m["Python"] for m in td.geographic_positions]
    msgs_as_jsonable = [m["JSONable"] for m in td.geographic_positions]
    invalid_msgs_as_python = [
        m["Python"] for m in td.invalid_geographic_positions
    ]

    @classmethod
    def define_models(cls):
        from esg.django_models.metadata import ProductTemplate
        from esg.django_models.metadata import PlantTemplate
        from esg.django_models.metadata import GeographicPositionTemplate

        class Product(ProductTemplate):
            """
            Create instance of model template.
            """

            class Meta:
                app_label = cls.__name__

        class Plant(PlantTemplate):
            class Meta:
                app_label = cls.__name__

            products = models.ManyToManyField(Product, related_name="plants")

        class GeographicPosition(GeographicPositionTemplate):
            class Meta:
                app_label = cls.__name__

            plant = models.OneToOneField(Plant, on_delete=models.DO_NOTHING)

        return [Product, Plant, GeographicPosition]

    def prepare_messages(self, msgs, msg_name):
        """
        Add foreign keys to positions.
        """
        if msg_name == "msgs_as_python":
            msgs = deepcopy(msgs)
            for i, msg in enumerate(msgs):
                msg["plant"] = self.Plant(name="test_plant_{}".format(i))
                msg["plant"].save()
        return msgs


@pytest.mark.skipif(django_unavailable, reason="requires django")
class TestPVSystem(GenericDjangoModelTemplateTest, GenericDjangoModelTestMixin):

    model_name = "PVSystem"
    msgs_as_python = [m["Python"] for m in td.pv_systems]
    msgs_as_jsonable = [m["JSONable"] for m in td.pv_systems]
    invalid_msgs_as_python = [m["Python"] for m in td.invalid_pv_systems]

    @classmethod
    def define_models(cls):
        from esg.django_models.metadata import ProductTemplate
        from esg.django_models.metadata import PlantTemplate
        from esg.django_models.metadata import PVSystemTemplate

        class Product(ProductTemplate):
            """
            Create instance of model template.
            """

            class Meta:
                app_label = cls.__name__

        class Plant(PlantTemplate):
            class Meta:
                app_label = cls.__name__

            products = models.ManyToManyField(Product, related_name="plants")

        class PVSystem(PVSystemTemplate):
            class Meta:
                app_label = cls.__name__

            plant = models.OneToOneField(Plant, on_delete=models.DO_NOTHING)
            # Ignore power_datapoint attribute. Testing it seems super hard.
            power_datapoint_id = None
            _power_datapoint = None

        return [Product, Plant, PVSystem]

    def prepare_messages(self, msgs, msg_name):
        """
        Add foreign keys to positions.
        """
        if msg_name == "msgs_as_python":
            msgs = deepcopy(msgs)
            for i, msg in enumerate(msgs):
                msg["plant"] = self.Plant(name="test_plant_{}".format(i))
                msg["plant"].save()

                del msg["power_datapoint_id"]

        if msg_name == "msgs_as_jsonable":
            msgs = deepcopy(msgs)
            for msg in msgs:
                if "power_datapoint_id" in msg:
                    msg["power_datapoint_id"] = None

        if msg_name == "invalid_msgs_as_python":
            msgs = deepcopy(msgs)
            for msg in msgs:
                if "power_datapoint_id" in msg:
                    del msg["power_datapoint_id"]

        return msgs


@pytest.mark.skipif(django_unavailable, reason="requires django")
class TestProductRun(
    GenericDjangoModelTemplateTest, GenericDjangoModelTestMixin
):
    """
    NOTE: Similar to TestPlant, this test cannot test plant_ids
    """

    model_name = "ProductRun"
    msgs_as_python = [m["Python"] for m in td.product_runs]
    msgs_as_jsonable = [m["JSONable"] for m in td.product_runs]
    invalid_msgs_as_python = [m["Python"] for m in td.invalid_product_runs]

    @classmethod
    def define_models(cls):
        from esg.django_models.metadata import ProductTemplate
        from esg.django_models.metadata import PlantTemplate
        from esg.django_models.metadata import ProductRunTemplate

        class Product(ProductTemplate):
            """
            Create instance of model template.
            """

            class Meta:
                app_label = cls.__name__

        class Plant(PlantTemplate):
            class Meta:
                app_label = cls.__name__

            products = models.ManyToManyField(Product, related_name="plants")

        class ProductRun(ProductRunTemplate):
            class Meta:
                app_label = cls.__name__

            _product = models.ForeignKey(
                Product,
                on_delete=models.CASCADE,
                # Must allow null as field will be null for a short time
                # during saving with `save_from_pydantic`
                null=True,
                related_name="product_runs",
            )
            plants = models.ManyToManyField(Plant, related_name="product_runs")

            @property
            def product_id(self):
                return self.get_fk_id_from_field(self._product)

            @product_id.setter
            def product_id(self, value):
                self._product = self.set_fk_obj_by_id(value, Product)

            @property
            def plant_ids(self):
                return []

            @plant_ids.setter
            def plant_ids(self, value):
                pass

        return [Product, Plant, ProductRun]

    def prepare_messages(self, msgs, msg_name):
        """
        Add IDs as DB does and related objects..
        """
        if msg_name in ["msgs_as_jsonable"]:
            msgs = deepcopy(msgs)
            for i, msg in enumerate(msgs):
                if msg["id"] is None:
                    msg["id"] = i + 1
                # Make the expectation matching the (hopefully only in test)
                # returned value.
                msg["plant_ids"] = []
        _ = self.Product(
            id=1,
            name="PVForecast",
            service_url="http://example.com/product_service/v1/",
            coverage_from=timedelta(days=0),
            coverage_to=timedelta(days=1),
        ).save()
        _ = self.Plant(id=1, name="Name").save()

        return msgs
