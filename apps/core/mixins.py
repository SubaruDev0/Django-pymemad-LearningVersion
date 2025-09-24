# mixins.py
from django.db import models

class TimestampedModel(models.Model):
    """Mixin para agregar created_at y updated_at"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
