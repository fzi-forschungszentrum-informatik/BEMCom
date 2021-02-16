from copy import deepcopy
from rest_framework.permissions import DjangoModelPermissions

class DjangoModelPermissionWithViewRestricted(DjangoModelPermissions):

    def __init__(self):
        self.perms_map = deepcopy(self.perms_map)
        self.perms_map['GET'] = ['%(app_label)s.view_%(model_name)s']
