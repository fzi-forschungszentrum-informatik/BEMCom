from django.urls import path
from django.contrib import admin


admin.site.site_header = "BEMCom Admin"
admin.site.site_title = "BEMCom"
admin.site.index_title = "Connector and Datapoint Adminsitration"

urlpatterns = [
    path('', admin.site.urls),
]
