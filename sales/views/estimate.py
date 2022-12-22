from rest_framework import generics, permissions

from sales.models.estimate import POFormula
from sales.serializers.estimate import POFormulaSerializer


class POFormulaList(generics.ListCreateAPIView):
    queryset = POFormula.objects.all()
    serializer_class = POFormulaSerializer
    permission_classes = [permissions.IsAuthenticated]


class POFormulaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = POFormula.objects.all()
    serializer_class = POFormulaSerializer
    permission_classes = [permissions.IsAuthenticated]
