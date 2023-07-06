from django.conf import settings
from django.http import HttpResponse
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.decorators import api_view
from decouple import config

from base.models.payment import Product
from base.serializers.payment import ProductSerializer, CheckoutSessionSerializer

stripe.api_key = config('STRIPE_SECRET_KEY', '')


class ProductPreview(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Product.objects.all()


class ProductPreviewDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Product.objects.all()


class CreateCheckOutSession(APIView):
    def post(self, request, *args, **kwargs):
        try:
            serializer = CheckoutSessionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data_insert = dict(serializer.validated_data)
            checkout_session = stripe.checkout.Session.create(
                line_items=[
                    {
                        'price': data_insert['price'],
                        'quantity': data_insert['quantity']
                    },
                ],
                metadata={
                    "stripe_email": self.request.user.email
                },
                mode='subscription',
                success_url="http://localhost:3000/success",
                cancel_url="http://localhost:3000/cancel.html",
                client_reference_id='1'
            )
            return redirect(checkout_session.url)
        except stripe.error.StripeError as e:
            return Response({'msg': 'something went wrong while creating stripe session', 'error': str(e)}, status=500)


@api_view(['POST'])
@csrf_exempt
def stripe_webhook_view(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_SECRET_WEBHOOK
        )
    except ValueError as e:
        # Invalid payload
        return Response(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return Response(status=400)
    if event['type'] == 'payment_intent.succeeded':
        pass
    return HttpResponse(status=200)


@api_view(['POST'])
def stripe_cancel_subscription(request):
    try:
        stripe.Subscription.modify(
            "sub_1NOBmEE4OZckNkJ5HNCkDDmn",
            cancel_at_period_end=True,
        )
    except Exception as ex:
        return HttpResponse(status=400)
    return HttpResponse(status=200)

