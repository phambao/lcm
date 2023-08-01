from rest_framework import serializers

from base.models.payment import Product, PaymentHistoryStripe


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class CheckoutSessionSerializer(serializers.Serializer):
    price = serializers.CharField()
    quantity = serializers.IntegerField()


class PaymentHistoryStripeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistoryStripe
        fields = '__all__'
