from django.conf import settings
from django.http import HttpResponse
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from decouple import config

from base.models.payment import Product, PaymentHistoryStripe
from base.serializers.payment import ProductSerializer, CheckoutSessionSerializer, PaymentHistoryStripeSerializer

stripe.api_key = config('STRIPE_SECRET_KEY', '')


class ProductPreview(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Product.objects.all()


class ProductPreviewDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Product.objects.all()


class PaymentHistoryStripePreview(generics.ListCreateAPIView):
    serializer_class = PaymentHistoryStripeSerializer
    queryset = PaymentHistoryStripe.objects.all()


class CreateCheckOutSession(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # serializer = CheckoutSessionSerializer(data=request.data)
            # serializer.is_valid(raise_exception=True)
            # data_insert = dict(serializer.validated_data)
            checkout_session = stripe.checkout.Session.create(
                line_items=[
                    {
                        'price': 'price_1NSAw2E4OZckNkJ5fvwlIRxN',
                        'quantity': 1
                    },
                ],
                metadata={
                    "stripe_email": 'truong123@gmail.com'
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
            payload, sig_header, config('STRIPE_SECRET_WEBHOOK')
        )

    except ValueError as e:
        # Invalid payload
        return Response(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return Response(status=400)
    if event['type'] == 'charge.succeeded':
        customer = stripe.Customer.create(
            email='daylatruong1@gmail.com',
            name='truonganh9988',
            invoice_prefix='TTKEWYGGEL'
        )
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[
                {
                    'price': 'price_1NSAw2E4OZckNkJ5fvwlIRxN',  # ID của giá cả hàng tháng/tuần/năm
                }
            ]
        )
    if event['type'] == 'customer.created':
        pass
    if event['type'] == 'invoice.created':

        customer_id = event['data']['object']['customer']
        stripe.Customer.delete(customer_id)
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


@api_view(['GET'])
@csrf_exempt
def get_config(request):
    prices = stripe.Price.list(
        # lookup_keys=['sample_basic', 'sample_premium']
    )
    return Response(
        {'publishable_key': config('STRIPE_PUBLIC_KEY'),
         'prices': prices.data},
    )


@api_view(['POST'])
@csrf_exempt
def create_customer(request):
    data = request.data
    try:
        customer = stripe.Customer.create(
            email=data['email'],
            name=data['name'],
            invoice_prefix=data['invoice_prefix']
        )
        resp = Response({'customer': customer})
        resp.set_cookie('customer', customer.id)

        return resp
    except Exception as e:
        return Response({'error': str(e)}, status=403)


@api_view(['POST'])
@csrf_exempt
def create_subscription(request):
    data = request.data
    customer_id = request.COOKIES.get('customer')
    price_id = data['price_id']
    try:
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{
                'price': price_id,
            }],
            payment_behavior='default_incomplete',
            expand=['latest_invoice.payment_intent'],
        )
        return Response({'subscription_id': subscription.id,
                        'client_secret': subscription.latest_invoice.payment_intent.client_secret})
    except Exception as e:
        return Response({'error': {'message': str(e)}}, status=400)


@api_view(['DELETE'])
@csrf_exempt
def cancel_subscription(request):
    data = request.body
    try:
        deleted_subscription = stripe.Subscription.delete(data['subscriptionId'])
        return Response({'subscription': deleted_subscription})
    except Exception as e:
        return Response({'error': str(e)}, status=403)


@api_view(['GET'])
@csrf_exempt
def list_subscriptions(request):
    customer_id = request.COOKIES.get('customer')
    try:
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            status='all',
            expand=['data.default_payment_method']
        )
        return Response({'subscriptions': subscriptions})
    except Exception as e:
        return Response({'error': str(e)}, status=403)


@api_view(['GET'])
@csrf_exempt
def preview_invoice(request):
    customer_id = request.COOKIES.get('customer')
    subscription_id = request.GET.get('subscription_id')
    new_price_lookup_key = request.GET.get('new_price_lookupKey')
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        invoice = stripe.Invoice.upcoming(
            customer=customer_id,
            subscription=subscription_id,
            subscription_items=[{
                'id': subscription['items']['data'][0].id,
                'price': new_price_lookup_key,
            }],
        )
        return Response({'invoice': invoice})
    except Exception as e:
        return Response({'error': str(e)}, status=403)


@api_view(['PUT'])
@csrf_exempt
def update_subscription(request):
    data = request.body
    try:
        subscription = stripe.Subscription.retrieve(data['subscription_id'])
        update_subscription = stripe.Subscription.modify(
            data['subscription_id'],
            items=[{
                'id': subscription['items']['data'][0].id,
                'price': data['new_price_lookup_key'].upper(),
            }]
        )
        return Response({'update_subscription': update_subscription})
    except Exception as e:
        return Response({'error': str(e)}, status=403)

import json
@csrf_exempt
def webhook_received(request):
    webhook_secret = config('STRIPE_SECRET_WEBHOOK')
    request_data = request.body
    if webhook_secret:
        signature = request.META['HTTP_STRIPE_SIGNATURE']
        try:
            # payload = json.dumps(request_data, separators=(',', ':'), sort_keys=True).encode('utf-8')
            event = stripe.Webhook.construct_event(
                request_data, signature,'whsec_9e199d91e07b5b7a61cfc34c3ebf882d1553e681d5ee03448133c84486e16419')
            data = event['data']
        except ValueError as e:
            return Response({'error': str(e)})

        except stripe.error.SignatureVerificationError as e:
            print('false')
            return Response({'error': str(e)})
        except Exception as e:
            return Response({'error': str(e)})
        event_type = event['type']
    else:
        data = request_data['data']
        event_type = request_data['type']
    data_object = data['object']
    print('***************')
    if event_type == 'invoice.payment_succeeded':
        if data_object['billing_reason'] == 'subscription_create':
            subscription_id = data_object['subscription']
            payment_intent_id = data_object['payment_intent']
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            stripe.Subscription.modify(
                subscription_id,
                default_payment_method=payment_intent.payment_method
            )
            print('passssss')
            payment_history = PaymentHistoryStripe.objects.create(
                subscription_id=subscription_id
            )
            print(payment_history)
            print("Default payment method set for subscription:" + payment_intent.payment_method)

    if event_type == 'customer.subscription.created':
        subscription_id = data_object.stripe_id
        payment_history = PaymentHistoryStripe.objects.create(
            subscription_id=subscription_id
        )
    elif event_type == 'invoice.payment_failed':
        print('Invoice payment failed: %s', event.id)
    elif event_type == 'invoice.finalized':
        print('Invoice finalized: %s', event.id)
    elif event_type == 'customer.subscription.deleted':
        print('Subscription canceled: %s', event.id)
    return Response({'status': 'success'})
    # payload = request.body
    # sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    # event = None
    #
    # try:
    #     event = stripe.Webhook.construct_event(
    #         payload, sig_header, 'whsec_9e199d91e07b5b7a61cfc34c3ebf882d1553e681d5ee03448133c84486e16419'
    #     )
    # except ValueError as e:
    #     # Invalid payload
    #     return HttpResponse(status=400)
    # except stripe.error.SignatureVerificationError as e:
    #     # Invalid signature
    #     return HttpResponse(status=400)
    #
    # # Handle the event
    # if event.type == 'payment_intent.succeeded':
    #     payment_intent = event.data.object  # contains a stripe.PaymentIntent
    #     print('PaymentIntent was successful!')
    # elif event.type == 'payment_method.attached':
    #     payment_method = event.data.object  # contains a stripe.PaymentMethod
    #     print('PaymentMethod was attached to a Customer!')
    # # ... handle other event types
    # else:
    #     print('Unhandled event type {}'.format(event.type))
    #
    # return HttpResponse(status=200)
