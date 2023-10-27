import datetime

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from rest_framework import permissions, status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from decouple import config
import jwt

from api.models import CompanyBuilder
from base.tasks import celery_send_mail
from base.models.payment import Product, PaymentHistoryStripe, Price
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
        expand=['data.product']
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
            name=data['name']
        )
        data_company = CompanyBuilder.objects.filter(pk=data['company'])
        data_company.customer_stripe = customer.id
        data_company.update(**{'customer_stripe': customer.id})
        resp = Response({'customer': customer})
        # resp.set_cookie('customer', customer.id)

        return resp
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['PUT'])
@csrf_exempt
def update_customer(request, *args, **kwargs):
    customer_id = kwargs.get('customer_id')
    data = request.data
    try:
        customer = stripe.Customer.modify(
            customer_id,
            email=data['email'],
            name=data['name'],
            invoice_prefix=data['invoice_prefix']
        )
        resp = Response({'customer': customer})

        return resp
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
def check_promotion_code(request):
    data = request.data
    promotion_code = data.get('coupon_code')
    try:
        promotion_codes = stripe.PromotionCode.list()
        coupon_id = None
        for code in promotion_codes:
            if code.code == promotion_code and code.active is True:
                if code.coupon.valid is True:
                    coupon_id = code
        if coupon_id is None:
            return Response({'error': {'message': 'Invalid promotion code'}}, status=400)
        return Response({'promotion': coupon_id})
    except Exception as e:
        return Response({'error': {'message': str(e)}}, status=400)


@api_view(['POST'])
@csrf_exempt
def create_subscription(request):
    data = request.data
    # customer_id = request.COOKIES.get('customer')
    price_id = data['price_id']
    customer_id = data['customer_id']
    promotion_code = data.get('coupon_code')
    try:
        if promotion_code == str():
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
        else:
            promotion_codes = stripe.PromotionCode.list()
            coupon_id = None
            for code in promotion_codes.data:
                if code.code == promotion_code:
                    coupon_id = code.coupon.id
                    break

            if coupon_id is None:
                return Response({'error': {'message': 'Invalid promotion code'}}, status=400)
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{
                    'price': price_id,
                }],
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent'],
                coupon=coupon_id
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


@api_view(['GET'])
@csrf_exempt
def preview_subscription(request, **kwargs):
    subscription_id = kwargs.get('subscription_id')
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        return Response({'subscription': subscription}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)


@csrf_exempt
def webhook_received(request):
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None
    try:
        event = stripe.Webhook.construct_event(
            request.body, sig_header, config('ENDPOINT_SECRET')
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)
    data = event['data']
    event_type = event['type']
    # Handle the event
    data_object = data['object']
    if event_type == 'price.updated':
        data_price = Price.objects.get(stripe_price_id=data_object['id'])
        data_price.amount = data_object['unit_amount']/100
        data_price.currency = data_object['currency']
        data_price.is_activate = data_object['active']
        data_price.save()

    if event_type == 'product.updated':
        data_product = Product.objects.get(stripe_product_id=data_object['id'])
        data_product.name = data_object['name']
        data_product.description = data_object['description']
        data_product.save()

    if event_type == 'invoice.payment_succeeded':
        subscription_id = data_object['subscription']
        payment_intent_id = data_object['payment_intent']
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        stripe.Subscription.modify(
            subscription_id,
            default_payment_method=payment_intent.payment_method
        )
        subscription = stripe.Subscription.retrieve(subscription_id,
                                                    expand=['plan.product'])
        payment_intent_id = data_object['payment_intent']
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id,
                                                       expand=['invoice', 'source', 'payment_method'])
        if data_object['billing_reason'] == 'subscription_create':

            customer_stripe_id = data_object.customer
            PaymentHistoryStripe.objects.create(
                subscription_id=subscription_id,
                customer_stripe_id=customer_stripe_id,
                payment_method_id=payment_intent.payment_method.id,
                subscription_name=subscription.plan.product.name,
                status=payment_intent.status,
                payment_method=payment_intent.payment_method.card.brand,
                card_number=payment_intent.payment_method.card.last4,
                price=payment_intent.amount,
                payment_day=payment_intent.created,
            )

        if data_object['billing_reason'] == 'subscription_cycle':
            customer_stripe_id = data_object.customer
            PaymentHistoryStripe.objects.create(
                subscription_id=subscription_id,
                customer_stripe_id=customer_stripe_id,
                payment_method_id=payment_intent.payment_method.id,
                subscription_name=subscription.plan.product.name,
                status=payment_intent.status,
                payment_method=payment_intent.payment_method.card.brand,
                card_number=payment_intent.payment_method.card.last4,
                price=payment_intent.amount,
                payment_day=payment_intent.created,
            )

    if event_type == 'payment_intent.payment_failed':
        payment_intent = stripe.PaymentIntent.retrieve(data_object.stripe_id,
                                                       expand=['invoice', 'source', 'payment_method'])
        subscription = stripe.Subscription.retrieve(payment_intent.invoice.lines.data[0].subscription,
                                                    expand=['plan.product'])

        brand = ''
        last4 = ''
        payment_method_id = ''
        payment_method = payment_intent.payment_method
        if payment_method:
            brand = payment_intent.payment_method.card.brand
            last4 = payment_intent.payment_method.card.last4
            payment_method_id = payment_intent.payment_method.id
        subscription_id = payment_intent.invoice.subscription
        customer_stripe_id = data_object.customer
        PaymentHistoryStripe.objects.create(
            subscription_id=subscription_id,
            customer_stripe_id=customer_stripe_id,
            payment_method_id=payment_method_id,
            subscription_name=subscription.plan.product.name,
            status=payment_intent.status,
            payment_method=brand,
            card_number=last4,
            price=payment_intent.amount,
            payment_day=payment_intent.created,
        )

    if event.type == 'payment_intent.succeeded':
        # subscription_id = data_object.stripe_id
        payment_intent = stripe.PaymentIntent.retrieve(data_object.stripe_id, expand=['invoice', 'source', 'payment_method'])
        subscription = stripe.Subscription.retrieve(payment_intent.invoice.lines.data[0].subscription, expand=['plan.product'])
        subscription_id = payment_intent.invoice.subscription
        customer_stripe_id = data_object.customer
        data_payment_history = PaymentHistoryStripe.objects.filter(
            subscription_id=subscription_id,
            customer_stripe_id=customer_stripe_id
        )
        # PaymentHistoryStripe.objects.create(
        #     subscription_id=subscription_id,
        #     customer_stripe_id=customer_stripe_id,
        #     payment_method_id=payment_intent.payment_method.id,
        #     subscription_name=subscription.plan.product.name,
        #     status=payment_intent.status,
        #     payment_method=payment_intent.payment_method.card.brand,
        #     card_number=payment_intent.payment_method.card.last4,
        #     price=payment_intent.amount,
        #     payment_day=payment_intent.created,
        # )
        if not data_payment_history:
            payload = {
                'sub': subscription_id,
                'customer': customer_stripe_id,
            }
            customer = stripe.Customer.retrieve(customer_stripe_id)
            jwt_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
            registration_link = f'{settings.BASE_URL}/register/?link={jwt_token.decode()}'
            content = render_to_string('auth/link-create-account.html', {'registration_link': registration_link})
            celery_send_mail.delay(f'Create account',
                                   content, settings.EMAIL_HOST_USER, [customer.email], False)
    elif event.type == 'payment_method.attached':
        pass

    return HttpResponse(status=200)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_payment_history(request):
    payment_history = PaymentHistoryStripe.objects.filter(customer_stripe_id=request.user.company.customer_stripe)
    paginator = LimitOffsetPagination()
    data_rs = paginator.paginate_queryset(payment_history, request)
    serializer = PaymentHistoryStripeSerializer(data_rs, many=True)
    return paginator.get_paginated_response(serializer.data)

