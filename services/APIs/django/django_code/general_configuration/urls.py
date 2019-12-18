"""manager URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from admin_interface.views import \
    AddConnectorView, ConnectorListView, EditConnectorView, \
    DeleteConnectorView, ConnectorDetailView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('connectors/', ConnectorListView.as_view(), name="connector_list"),
    path('connectors/add', AddConnectorView.as_view(), name="add_connector"),
    path('connectors/edit/<int:id>', EditConnectorView.as_view(), name="edit_connector"),
    path('connectors/delete/<int:id>', DeleteConnectorView.as_view(), name="delete_connector"),
    path('connectors/detail/<int:id>', ConnectorDetailView.as_view(), name="connector_detail"),
]
