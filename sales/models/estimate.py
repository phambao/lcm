from django.db import models

from api.models import BaseModel


class POFormula(BaseModel):
    name = models.CharField(max_length=128)
    formula = models.CharField(max_length=256)
    text_formula = models.TextField(max_length=256)
