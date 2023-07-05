from rest_framework import serializers

from base.models.payment import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class CheckoutSessionSerializer(serializers.Serializer):
    price = serializers.CharField()
    quantity = serializers.IntegerField()
