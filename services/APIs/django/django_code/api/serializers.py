from rest_framework import serializers

from admin_interface.models.datapoint import Datapoint


class DatapointSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Datapoint
        fields = ["id", "url", "data_format", "description"]
