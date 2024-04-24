from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
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

from api.models import CompanyBuilder, User, SubscriptionStripeCompany
from base.constants import PERCENT_DISCOUNT
from base.tasks import celery_send_mail
from base.models.payment import Product, PaymentHistoryStripe, Price, ReferralCode, DealerInformation, DealerCompany, \
    CouponCode
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


@api_view(['DELETE'])
def stripe_cancel_subscription(request, *args, **kwargs):
    subscription_id = kwargs.get('subscription_id')
    try:
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True,
        )
        # deleted_subscription = stripe.Subscription.delete(subscription_id)
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
            name=data['name'],
            metadata={"company": data['company']}
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
def check_promotion_code_v2(request):
    data = request.data
    promotion_code = data.get('coupon_code')
    products = data.get('products')
    type_coupon = data.get('type')
    total_discount = 0
    total_discount_sign_up = 0
    total_discount_product = 0
    total_discount_pro_launch = 0
    try:
        coupon_id = None
        rs_coupon = []
        for data_code in promotion_code:
            promotion_codes = stripe.PromotionCode.list(limit=100000)
            for code in promotion_codes:
                if code.code == data_code['code'] and code.active:
                    if code.coupon.valid:
                        amount_off = code.coupon.amount_off
                        percent_off = code.coupon.percent_off
                        coupon_id = code
                        rs_coupon.append(code)
                        data_coupon = None
                        if data_code['type'] == 'coupon':
                            data_coupon = CouponCode.objects.get(coupon_stripe_id=coupon_id.coupon.id)

                        else:
                            data_coupon = ReferralCode.objects.get(coupon_stripe_id=coupon_id.coupon.id)

                        for product in products:
                            if product['type'] == 'recurring':
                                if percent_off:
                                    total_discount_product += (product['amount'] * int(percent_off)) / 100
                                    total_discount += (product['amount'] * int(percent_off)) / 100
                                    product['amount'] = product['amount'] - (product['amount'] * int(percent_off)) / 100

                                if amount_off:
                                    total_discount_product += int(amount_off)
                                    total_discount += int(amount_off)
                                    product['amount'] = product['amount'] - int(amount_off)

                            elif product['type'] == 'one_time' and not product['is_launch']:

                                if data_coupon.percent_discount_sign_up:
                                    total_discount_sign_up += (product['amount'] * int(data_coupon.percent_discount_sign_up)) / 100
                                    total_discount += (product['amount'] * int(data_coupon.percent_discount_sign_up)) / 100
                                    product['amount'] = product['amount'] - (product['amount'] * int(data_coupon.percent_discount_sign_up)) / 100

                                if data_coupon.number_discount_sign_up:
                                    total_discount_sign_up += int(data_coupon.number_discount_sign_up)
                                    total_discount += int(data_coupon.number_discount_sign_up)
                                    product['amount'] = product['amount'] - int(data_coupon.number_discount_sign_up)

                            elif product['type'] == 'one_time' and product['is_launch']:
                                if data_coupon.percent_discount_pro_launch:
                                    total_discount_pro_launch += (product['amount'] * int(data_coupon.percent_discount_pro_launch)) / 100
                                    total_discount += (product['amount'] * int(data_coupon.percent_discount_pro_launch)) / 100
                                    product['amount'] = product['amount'] - (product['amount'] * int(data_coupon.percent_discount_pro_launch)) / 100

                                if data_coupon.number_discount_pro_launch:
                                    total_discount_pro_launch += int(data_coupon.number_discount_pro_launch)
                                    total_discount += int(data_coupon.number_discount_pro_launch)
                                    product['amount'] = product['amount'] - int(data_coupon.number_discount_pro_launch)

        if not coupon_id:
            return Response({'error': {'message': 'Invalid promotion code'}}, status=400)
        return Response({'promotion': rs_coupon, 'total_discount': total_discount,
                         'coupon_id': 'abc',
                         'total_discount_product': total_discount_product,
                         'total_discount_sign_up': total_discount_sign_up,
                         'total_discount_pro_launch': total_discount_pro_launch})
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
                coupon=coupon_id,
            )
            return Response({'subscription_id': subscription.id,
                             'client_secret': subscription.latest_invoice.payment_intent.client_secret})
    except Exception as e:
        return Response({'error': {'message': str(e)}}, status=400)


@api_view(['POST'])
@csrf_exempt
def create_subscription_v2(request):
    data = request.data
    # customer_id = request.COOKIES.get('customer')
    prices_create = []
    prices = data['prices']
    # price_id = data['price_id']
    customer_id = data['customer_id']
    promotion_code = data.get('coupon_code')
    coupon_id = data.get('coupon_id')
    referral_code_id = data.get('referral_code_id')
    total_amount_price = 0
    total_discount_amount = 0
    prices_one_time = []
    price_recurring = None
    total_product_amount = 0
    total_sign_up_fee = 0
    total_pro_launch = 0
    data_coupon = None
    data_referral = None
    for price in prices:
        data_price = stripe.Price.retrieve(price['id'])
        metadata = data_price.metadata
        price_create = {'price': price['id']}
        prices_create.append(price_create)
        total_amount_price += data_price['unit_amount']
        if data_price['type'] == 'recurring':
            price_recurring = data_price['id']
            total_product_amount = data_price['unit_amount']

        elif data_price['type'] == 'one_time' and not metadata:
            data_create = {"price": data_price['id']}
            prices_one_time.append(data_create)
            total_sign_up_fee = data_price['unit_amount']

        elif data_price['type'] == 'one_time' and metadata:
            data_create = {"price": data_price['id']}
            prices_one_time.append(data_create)
            total_pro_launch = data_price['unit_amount']

    if coupon_id:
        data_coupon = CouponCode.objects.get(coupon_stripe_id=coupon_id)
        rs_product, rs_sign_fee, rs_pro_launch, discount_amount = handle_total_discount(total_sign_up_fee, total_product_amount,total_pro_launch, data_coupon, prices)
        total_discount_amount += discount_amount
        total_product_amount = rs_product
        total_sign_up_fee = rs_sign_fee
        total_pro_launch = rs_pro_launch

    if referral_code_id:
        data_referral = ReferralCode.objects.get(coupon_stripe_id=referral_code_id)
        rs_product, rs_sign_fee, rs_pro_launch, discount_amount = handle_total_discount(total_sign_up_fee, total_product_amount, total_pro_launch, data_referral, prices)
        total_discount_amount += discount_amount
        total_product_amount = rs_product
        total_sign_up_fee = rs_sign_fee
        total_pro_launch = rs_pro_launch

    try:
        if not promotion_code:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{
                    'price': price_recurring,
                }],
                add_invoice_items=prices_one_time,
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent'],
            )
            return Response({'subscription_id': subscription.id,
                             'client_secret': subscription.latest_invoice.payment_intent.client_secret})
        else:
            coupon = stripe.Coupon.create(
                amount_off=int(total_discount_amount),
                currency="usd",
                duration="repeating",
                name="Discount",
                duration_in_months=12,
                metadata={
                    'referral_code': referral_code_id,
                    'coupon_id': coupon_id,
                }
            )
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{
                    'price': price_recurring,
                }],
                add_invoice_items=prices_one_time,
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent'],
                coupon=coupon,
            )
            return Response({'subscription_id': subscription.id,
                             'client_secret': subscription.latest_invoice.payment_intent.client_secret})
    except Exception as e:
        return Response({'error': {'message': str(e)}}, status=400)


def handle_total_discount(total_sign_up_fee,  total_product,  total_pro_launch,  data_coupon, prices):
    total_discount_amount = 0
    percent_off = data_coupon.percent_discount_product
    amount_off = data_coupon.number_discount_product
    for price in prices:
        data_price = stripe.Price.retrieve(price['id'])
        metadata = data_price.metadata
        amount = data_price['unit_amount']
        if price['type'] == 'recurring':
            if percent_off:
                total_discount_amount += (total_product * int(percent_off)) / 100
                total_product = total_product - (total_product * int(percent_off)) / 100

            if amount_off:
                total_discount_amount += int(amount_off)
                total_product = total_product - int(amount_off)

        elif price['type'] == 'one_time' and not metadata:
            if data_coupon.percent_discount_sign_up:
                total_discount_amount += (total_sign_up_fee * int(data_coupon.percent_discount_sign_up)) / 100
                total_sign_up_fee = total_sign_up_fee - (total_sign_up_fee * int(data_coupon.percent_discount_sign_up)) / 100

            if data_coupon.number_discount_sign_up:
                total_discount_amount += int(data_coupon.number_discount_sign_up)
                total_sign_up_fee = total_sign_up_fee - int(data_coupon.number_discount_sign_up)

        elif price['type'] == 'one_time' and metadata:
            if data_coupon.percent_discount_pro_launch:
                total_discount_amount += (total_pro_launch * int(data_coupon.percent_discount_pro_launch)) / 100
                total_pro_launch = total_pro_launch - (total_pro_launch * int(data_coupon.percent_discount_pro_launch)) / 100

            if data_coupon.number_discount_pro_launch:
                total_discount_amount += int(data_coupon.number_discount_pro_launch)
                total_pro_launch = total_pro_launch - int(data_coupon.number_discount_pro_launch)

    return total_discount_amount, total_product, total_sign_up_fee, total_pro_launch


@api_view(['DELETE'])
@csrf_exempt
def cancel_subscription(request):
    data = request.body
    try:
        deleted_subscription = stripe.Subscription.delete(data['subscriptionId'])
        return Response({'subscription': deleted_subscription})
        # stripe.Subscription.modify(
        #     "sub_49ty4767H20z6a",
        #     cancel_at_period_end=True,
        # )
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
    if event_type == 'customer.subscription.deleted':
        subscription_id = data_object['id']
        data_subscription = SubscriptionStripeCompany.objects.get(subscription_id=subscription_id)
        dealer_company = DealerCompany.objects.get(company=data_subscription.company)
        dealer_company.is_activate = False
        dealer_company.save()
        data_subscription.delete()
        customer_stripe_id = data_object['customer']

        user = User.objects.get(stripe_customer=customer_stripe_id)
        company = user.company
        company.is_payment = False
        company.save()

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
            expiration_date = datetime.fromtimestamp(subscription.current_period_end)
            customer_stripe_id = data_object.customer
            customer = stripe.Customer.retrieve(customer_stripe_id)
            subscription_name = subscription.plan.product.name
            if data_object.discount:
                coupon_code = data_object.discount.coupon.id
                coupon = stripe.Coupon.retrieve(coupon_code)
                referral_code_id = coupon.metadata.get('referral_code', None)
                coupon_id = coupon.metadata.get('coupon_id', None)
                is_use_one = False
                data_referral_code = None
                company = None
                if referral_code_id:
                    data_referral_code = ReferralCode.objects.get(coupon_stripe_id=referral_code_id)
                    company = data_referral_code.company
                dealer = None
                if data_referral_code and data_referral_code.dealer:
                    dealer = DealerInformation.objects.get(user=data_referral_code.dealer.user)
                if company:
                    dealer_apply_for_ddr = None
                    data_subscription_stripe_company = SubscriptionStripeCompany.objects.filter(company=company).first()
                    if company.referral_code_current:
                        dealer_apply_for_ddr = company.referral_code_current.dealer

                    data_sub = stripe.Subscription.retrieve(data_subscription_stripe_company.subscription_id, expand=['plan.product'])
                    total_amount = data_sub.plan.amount/100
                    company_referral_code = company.referral_code_current
                    data_products = data_object.lines.data
                    commission_amount = 0
                    commission_amount_for_product_launch = 0
                    for product in data_products:
                        product_id = product.price.product
                        data_product = stripe.Product.retrieve(product_id)
                        metadata = data_product.metadata
                        is_launch = metadata.get('is_launch', None)
                        if is_launch and is_launch == 'True' and not product.price.recurring:
                            commission_amount += (product.price.unit_amount * 10) / 10000
                            commission_amount_for_product_launch = (product.price.unit_amount * 10) / 10000

                        elif not product.price.recurring:
                            commission_amount += (product.price.unit_amount * 50) / 10000

                    # handle for case dealer recept commission to product launch of DSR when subscription
                    if dealer_apply_for_ddr:
                        # dealer_for_ddr = referral_code.dealer
                        dealer_apply_for_ddr.total_bonus_commissions = dealer_apply_for_ddr.total_bonus_commissions + commission_amount_for_product_launch
                        dealer_apply_for_ddr.save()

                    if not dealer_apply_for_ddr:
                        referral = ReferralCode.objects.get(company=company, is_activate=True)
                        if not referral.percent_discount_sign_up and not referral.percent_discount_pro_launch and referral.percent_discount_product == PERCENT_DISCOUNT:
                            pass
                        else:
                            promotion_code_id = referral.promotion_code_id
                            referral.is_activate = False
                            referral.save()
                            if promotion_code_id:
                                promotion_code = stripe.PromotionCode.modify(
                                    promotion_code_id,
                                    active=False
                                )

                            coupon = stripe.Coupon.create(
                                percent_off=20,
                                duration='forever',

                                max_redemptions=referral.number_of_uses,
                                name=referral.title,
                            )

                            promotion_code = stripe.PromotionCode.create(
                                coupon=coupon,
                                code=referral.code,
                                metadata={
                                    'coupon_id': coupon.id
                                }
                            )
                            ReferralCode.objects.create(
                                title=referral.title,
                                code=referral.code,
                                description=referral.description,
                                percent_discount_product=20,
                                monthly_discounts=referral.monthly_discounts,
                                number_of_uses=referral.number_of_uses,
                                company=referral.company,
                                is_activate=True,
                                coupon_stripe_id=coupon.id,
                                promotion_code_id=promotion_code.id
                            )

                    discount_amount = 0
                    # check coupon code is once or repeating
                    if company_referral_code:
                        coupon_company = stripe.Coupon.retrieve(company_referral_code.coupon_stripe_id)
                        if coupon_company.duration == 'once':
                            is_use_one = True

                    if company_referral_code and company_referral_code.percent_discount_sign_up:
                        discount_amount = total_amount * company_referral_code.percent_discount_sign_up/100

                    elif company_referral_code and company_referral_code.number_discount_sign_up:
                        discount_amount = company_referral_code.number_discount_sign_up

                    company.credit = int(company.credit + commission_amount)
                    company.save()
                    # if company not coupon code when payment first
                    if not company_referral_code or is_use_one:
                        temp_amount = total_amount - discount_amount
                        create_referral_code = None
                        if company.credit >= temp_amount:
                            company.credit = company.credit - temp_amount

                            company.save()
                            coupon = stripe.Coupon.create(
                                percent_off=None,
                                amount_off=int(total_amount * 100),
                                currency=data_sub.currency,
                                duration='once',
                                max_redemptions=1
                            )
                            subscription = stripe.Subscription.modify(
                                data_subscription_stripe_company.subscription_id,
                                coupon=coupon,
                            )
                            create_referral_code = ReferralCode.objects.create(
                                number_discount_sign_up=total_amount,
                                currency=data_sub.currency,
                                coupon_stripe_id=coupon.id,
                                dealer=company_referral_code.dealer,
                            )
                        else:
                            total_discount_coupon = company.credit + discount_amount

                            company.credit = 0
                            company.save()
                            coupon = stripe.Coupon.create(
                                percent_off=None,
                                amount_off=int(total_discount_coupon * 100),
                                currency=data_sub.currency,
                                duration='once',
                                max_redemptions=1
                            )

                            subscription = stripe.Subscription.modify(
                                data_subscription_stripe_company.subscription_id,
                                coupon=coupon,
                            )

                            create_referral_code = ReferralCode.objects.create(
                                number_discount_sign_up=total_discount_coupon,
                                currency=data_sub.currency,
                                coupon_stripe_id=coupon.id,
                                dealer=data_referral_code.dealer,
                            )
                        company.referral_code_current = create_referral_code
                        company.save()

                    elif company_referral_code and discount_amount < total_amount and not is_use_one:
                        temp_amount = total_amount - discount_amount
                        create_referral_code = None
                        if company.credit >= temp_amount:
                            company.credit = company.credit - temp_amount
                            company.save()
                            coupon = stripe.Coupon.create(
                                percent_off=None,
                                amount_off=int(total_amount * 100),
                                currency=data_sub.currency,
                                duration='repeating',
                                duration_in_months=data_subscription_stripe_company.duration_in_months,
                            )
                            subscription = stripe.Subscription.modify(
                                data_subscription_stripe_company.subscription_id,
                                coupon=coupon,
                            )
                            create_referral_code = ReferralCode.objects.create(
                                number_discount_sign_up=total_amount,
                                currency=data_sub.currency,
                                coupon_stripe_id=coupon.id,
                                dealer=company_referral_code.dealer,
                            )
                        else:
                            total_discount_coupon = discount_amount + company.credit
                            company.credit = 0
                            company.save()
                            coupon = stripe.Coupon.create(
                                percent_off=None,
                                amount_off=int(total_discount_coupon * 100),
                                currency=data_sub.currency,
                                duration='repeating',
                                duration_in_months=data_subscription_stripe_company.duration_in_months,
                            )
                            subscription = stripe.Subscription.modify(
                                data_subscription_stripe_company.subscription_id,
                                coupon=coupon,
                            )
                            create_referral_code = ReferralCode.objects.create(
                                number_discount_sign_up=total_discount_coupon,
                                currency=data_sub.currency,
                                coupon_stripe_id=coupon.id,
                                dealer=company_referral_code.dealer,
                            )
                        company.referral_code_current = create_referral_code
                        company.save()
                if dealer:

                    data_products = data_object.lines.data
                    commission_amount = 0
                    for product in data_products:
                        product_id = product.price.product
                        data_product = stripe.Product.retrieve(product_id)
                        metadata = data_product.metadata
                        is_launch = metadata.get('is_launch', None)
                        if not metadata and is_launch == 'True' and not product.price.recurring:
                            commission_amount += (product.price.unit_amount * 20) / 10000

                        elif not product.price.recurring:
                            commission_amount += (product.price.unit_amount * 30) / 10000

                    dealer.total_bonus_commissions = dealer.total_bonus_commissions + commission_amount
                    dealer.save()
                    data_company = CompanyBuilder.objects.get(pk=customer.metadata['company'])
                    DealerCompany.objects.create(
                        dealer=dealer,
                        referral_code=data_referral_code,
                        company=data_company,
                        is_activate=True,
                        bonus_commissions=commission_amount
                    )
                new_discount_amount = 0

                if referral_code_id and coupon_id:
                    data_coupon_code = CouponCode.objects.get(coupon_stripe_id=coupon_id)
                    amount = subscription.plan.amount
                    if data_referral_code.number_discount_product:
                        new_discount_amount += amount - data_referral_code.number_discount_product

                    if data_referral_code.percent_discount_product:
                        new_discount_amount += (amount * data_referral_code.percent_discount_product) / 100

                    if data_coupon_code.number_discount_product:
                        new_discount_amount += amount - data_coupon_code.number_discount_product

                    if data_referral_code.percent_discount_product:
                        new_discount_amount += (amount * data_coupon_code.percent_discount_product) / 100

                elif referral_code_id and not coupon_id:

                    amount = subscription.plan.amount
                    if data_referral_code.number_discount_product:
                        new_discount_amount += amount - data_referral_code.number_discount_product

                    if data_referral_code.percent_discount_product:
                        new_discount_amount += (amount * data_referral_code.percent_discount_product) / 100

                elif coupon_id and not referral_code_id:
                    data_coupon_code = CouponCode.objects.get(coupon_stripe_id=coupon_id)
                    amount = subscription.plan.amount
                    if data_coupon_code.number_discount_product:
                        new_discount_amount += amount - data_coupon_code.number_discount_product

                    if data_referral_code.percent_discount_product:
                        new_discount_amount += (amount * data_coupon_code.percent_discount_product) / 100

                coupon = stripe.Coupon.create(
                    amount_off=int(new_discount_amount),
                    currency="usd",
                    duration='repeating',
                    duration_in_months=11,
                )

                subscription = stripe.Subscription.modify(
                    subscription_id,
                    coupon=coupon,
                )
                create_referral_code = ReferralCode.objects.create(
                    number_discount_product=int(new_discount_amount),
                    coupon_stripe_id=coupon.id,
                    dealer=data_referral_code.dealer
                )
                data_company = CompanyBuilder.objects.get(pk=customer.metadata['company'])
                data_company.referral_code_current = create_referral_code
                data_company.save()

            SubscriptionStripeCompany.objects.create(
                subscription_id=subscription_id,
                customer_stripe=customer_stripe_id,
                company_id=int(customer.metadata['company']),
                subscription_name=subscription_name,
                expiration_date=expiration_date,
                duration_in_months=data_object.discount.coupon.duration_in_months - 1,
                is_activate=True
            )
            product = stripe.Product.retrieve(subscription.plan.product)
            PaymentHistoryStripe.objects.create(
                subscription_id=subscription_id,
                customer_stripe_id=customer_stripe_id,
                payment_method_id=payment_intent.payment_method.id,
                subscription_name=product.name,
                status=payment_intent.status,
                payment_method=payment_intent.payment_method.card.brand,
                card_number=payment_intent.payment_method.card.last4,
                price=payment_intent.amount,
                payment_day=payment_intent.created,
            )

        if data_object['billing_reason'] == 'subscription_cycle':
            if data_object.discount:
                is_use_one = False
                coupon_code = data_object.discount.coupon.id
                coupon_company = stripe.Coupon.retrieve(coupon_code)
                if coupon_company.duration == 'once':
                    is_use_one = True

                data_referral_code = ReferralCode.objects.get(coupon_stripe_id=coupon_code)
                # dealer = DealerInformation.objects.get(user=data_referral_code.dealer.user)
                company = CompanyBuilder.objects.get(pk=customer.metadata['company'])
                if company:
                    data_subscription_stripe_company = SubscriptionStripeCompany.objects.filter(company=company).first()
                    total_amount = subscription.plan.amount / 100
                    company_referral_code = company.referral_code_current
                    discount_amount = 0
                    if is_use_one:
                        create_referral_code = None
                        if company.credit >= total_amount:
                            coupon = stripe.Coupon.create(
                                percent_off=None,
                                amount_off=int((company.credit - total_amount) * 100),
                                currency=subscription.currency,
                                duration='once',
                                max_redemptions=1
                            )
                            company.credit = company.credit - total_amount
                            company.save()
                            subscription = stripe.Subscription.modify(
                                data_subscription_stripe_company.subscription_id,
                                coupon=coupon,
                            )
                            create_referral_code = ReferralCode.objects.create(
                                number_discount_sign_up=total_amount,
                                currency=subscription.currency,
                                coupon_stripe_id=coupon.id,
                                dealer=data_referral_code.dealer,

                            )

                        else:
                            coupon = stripe.Coupon.create(
                                percent_off=None,
                                amount_off=int(company.credit * 100),
                                currency=subscription.currency,
                                duration='once',
                                max_redemptions=1
                            )
                            company.credit = 0
                            company.save()
                            subscription = stripe.Subscription.modify(
                                data_subscription_stripe_company.subscription_id,
                                coupon=coupon,
                            )
                            create_referral_code = ReferralCode.objects.create(
                                number_discount_sign_up=total_amount,
                                currency=subscription.currency,
                                coupon_stripe_id=coupon.id,
                                dealer=data_referral_code.dealer,

                            )
                        company.referral_code_current = create_referral_code
                        company.save()
                    else:
                        discount_amount = total_amount * 30/100
                        if discount_amount < total_amount:
                            temp_amount = total_amount - discount_amount
                            create_referral_code = None
                            if company.credit >= temp_amount:
                                company.credit = company.credit - temp_amount
                                company.save()
                                coupon = stripe.Coupon.create(
                                    percent_off=None,
                                    amount_off=int(total_amount * 100),
                                    currency=subscription.currency,
                                    duration='repeating',
                                    duration_in_months=data_subscription_stripe_company.duration_in_months - 1,
                                )
                                subscription = stripe.Subscription.modify(
                                    data_subscription_stripe_company.subscription_id,
                                    coupon=coupon,
                                )
                                create_referral_code = ReferralCode.objects.create(
                                    number_discount_sign_up=total_amount,
                                    currency=subscription.currency,
                                    coupon_stripe_id=coupon.id,
                                    dealer=data_referral_code.dealer,

                                )

                            else:
                                total_discount_coupon = discount_amount + company.credit
                                company.credit = 0
                                company.save()
                                coupon = stripe.Coupon.create(
                                    percent_off=None,
                                    amount_off=int(total_discount_coupon * 100),
                                    currency=subscription.currency,
                                    duration='repeating',
                                    duration_in_months=data_subscription_stripe_company.duration_in_months - 1,
                                )
                                subscription = stripe.Subscription.modify(
                                    subscription.id,
                                    coupon=coupon,
                                )
                                create_referral_code = ReferralCode.objects.create(
                                    number_discount_sign_up=total_discount_coupon,
                                    currency=subscription.currency,
                                    coupon_stripe_id=coupon.id,
                                    dealer=data_referral_code.dealer,

                                )

                            company.referral_code_current = create_referral_code
                            company.save()

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

    elif event.type == 'charge.failed':
        payment_intent = stripe.PaymentIntent.retrieve(data_object['payment_intent'],
                                                       expand=['invoice', 'source', 'payment_method'])
        subscription = stripe.Subscription.retrieve(payment_intent.invoice.lines.data[0].subscription,
                                                    expand=['plan.product'])

        customer = data_object['customer']
        user = User.objects.get(stripe_customer=customer)
        company_name = user.company.company_name
        customer_name = user.username
        # url = BASE_URL
        url_login = config('BASE_URL') + '/login/'
        content = render_to_string('auth/payment-failse.html', {
            'subscription_name': subscription.plan.product.name,
            'company_name': company_name,
            'customer_name': customer_name,
            'url_login': url_login
        })
        celery_send_mail.delay(f'Stripe Fail Payment - this is a test',
                               content, settings.EMAIL_HOST_USER, [user.email], False)
    return HttpResponse(status=200)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_payment_history(request):
    payment_history = PaymentHistoryStripe.objects.filter(customer_stripe_id=request.user.company.customer_stripe)
    paginator = LimitOffsetPagination()
    data_rs = paginator.paginate_queryset(payment_history, request)
    serializer = PaymentHistoryStripeSerializer(data_rs, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
def get_data_dealer(request, period):
    if request.method == 'GET' and request.user.is_authenticated:
        dealer_info = DealerInformation.objects.get(user=request.user)
        total_amount = 0
        total_user = 0
        end_date = datetime.now()
        start_date = None
        if period == 'week':
            start_date = end_date - timedelta(days=7)

        elif period == 'month':
            start_date = end_date - timedelta(days=30)

        elif period == 'year':
            start_date = end_date - timedelta(days=365)

        if start_date:
            data_dealer = DealerCompany.objects.filter(created_at__gte=start_date, created_at__lt=end_date, dealer=dealer_info)
            total_user = len(data_dealer)
            for data in data_dealer:
                total_amount += data.bonus_commissions
        else:
            data_dealer = DealerCompany.objects.filter(dealer=dealer_info)
            total_user = len(data_dealer)
            total_amount = dealer_info.total_bonus_commissions

        return Response(status=status.HTTP_200_OK, data={'data': total_amount, 'total_user': total_user})
    else:
        return Response(status=status.HTTP_404_NOT_FOUND)