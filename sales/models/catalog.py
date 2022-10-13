from django.db import models
from django.utils.translation import gettext_lazy as _

from api.models import BaseModel


class Material(BaseModel):
    
    class Meta:
        db_table = 'material'
        
    name = models.CharField(max_length=128)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    children = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='children_material')
    
    def __str__(self):
        return self.name
    