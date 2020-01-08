from django.apps import AppConfig
#from django.db.models import signals


class AdminInterfaceConfig(AppConfig):
    name = 'admin_interface'

    def ready(self):
        import admin_interface.signals

