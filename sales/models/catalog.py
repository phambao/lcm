from django.db import models

from api.models import BaseModel


class Material(BaseModel):

    class Meta:
        db_table = 'material'

    sequence = models.IntegerField(default=0)
    name = models.CharField(max_length=128)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=128, null=True, blank=True)

    def __str__(self):
        return self.name
