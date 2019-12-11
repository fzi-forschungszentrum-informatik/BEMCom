from django.contrib import admin
from . import models


class ConnectorAdmin(admin.ModelAdmin):
    hb = "heartbeat"
    prepopulated_fields = {"mqtt_topic_heartbeat": ("name",)}


# Register your models here.
admin.site.register(models.Connector, ConnectorAdmin)
admin.site.register(models.Device)