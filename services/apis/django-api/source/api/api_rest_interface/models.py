from django.db import models

class Metric(models.Model):
    """
    This model is not intended to store anything in DB. It is just a
    quick and dirty trick to get permission checking and stuff for the
    metrics/ endpoint.
    """
