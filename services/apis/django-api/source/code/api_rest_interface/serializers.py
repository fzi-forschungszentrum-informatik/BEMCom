from rest_framework import serializers

from api_main.models.datapoint import Datapoint


class DatapointSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer matching the fields of the Datapoint model of the API.
    """

    class Meta:
        model = Datapoint
        fields = [
            "id",
            "type",
            "data_format",
            "short_name",
            "description",
            "min_value",
            "max_value",
            "allowed_values",
            "unit",
            ]
        read_only_fields = [
            "id",
        ]
