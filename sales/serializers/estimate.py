from rest_framework import serializers

from sales.models.estimate import POFormula


class POFormulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = POFormula
        fields = ('id', 'name', 'formula', 'text_formula')
