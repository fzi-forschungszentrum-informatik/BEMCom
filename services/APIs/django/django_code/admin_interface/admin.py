from django.contrib import admin
from . import models

# Register your models here.
admin.site.register(models.Connector)
admin.site.register(models.Device)