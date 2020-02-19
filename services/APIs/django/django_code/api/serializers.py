from rest_framework import serializers

from admin_interface.models.datapoint import Datapoint


class DatapointSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Datapoint
        fields = ["url", "use_as", "type", "key_in_connector", ]
