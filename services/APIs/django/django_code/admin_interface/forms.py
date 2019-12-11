from django import forms
from . import models


class ConnectorForm(forms.ModelForm):
    class Meta:
        model = models.Connector
        fields = "__all__"

    def save(self):
        connector = super(ConnectorForm, self).save(commit=False)
        connector.save()
        return connector
