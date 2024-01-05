import decimal
from rest_framework import serializers


def quantize(self, value):
    """
    Quantize the decimal value to the configured precision.
    """
    if self.decimal_places is None:
        return value

    context = decimal.getcontext().copy()
    if self.max_digits is not None:
        context.prec = self.max_digits
    return value.quantize(
        decimal.Decimal('.1') ** self.decimal_places,
        rounding=self.rounding,
        context=context
    ).normalize()

serializers.DecimalField.quantize = quantize
