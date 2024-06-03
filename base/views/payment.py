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
from base.constants import PERCENT_DISCOUNT, YEAR, MONTH, WEEK
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
        expand=['data.product']
    )
    active_prices = [price for price in prices.data if price.product['active']]
    return Response(
        {'publishable_key': config('STRIPE_PUBLIC_KEY'),
         'prices': active_prices},
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
    total_discount = 0
    total_discount_sign_up = 0
    total_discount_product = 0
    total_discount_pro_launch = 0
    try:
        coupon_id = None
        rs_coupon = []
        for data_code in promotion_code:
            promotion_codes = stripe.PromotionCode.list(code=data_code['code'])
            code = None
            if promotion_codes.data:
                code = promotion_codes.data[0]
            if code and code.code == data_code['code'] and code.active:
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
                        company = data_coupon.company
                        if company and not company.referral_code_current:
                            data_coupon.percent_discount_sign_up = None
                            data_coupon.percent_discount_pro_launch = None
                            data_coupon.save()

                        if company and company.referral_code_current and not company.referral_code_current.dealer:
                            data_coupon.percent_discount_sign_up = None
                            data_coupon.percent_discount_pro_launch = None
                            data_coupon.save()

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
            else:
                return Response({'error': {'message': 'Invalid promotion code'}}, status=400)
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
    prices_create = []
    prices = data['prices']
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
    discounts = []
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
            coupon = None
            if total_discount_amount > 0:
                coupon = stripe.Coupon.create(
                    amount_off=int(total_discount_amount),
                    currency="usd",
                    duration="once",
                    name="Discount",
                    max_redemptions=1,
                    metadata={
                        'referral_code': referral_code_id,
                        'coupon_id': coupon_id,
                    }
                )
            if coupon_id:
                discounts.append({"coupon": coupon_id})

            if referral_code_id:
                discounts.append({"coupon": referral_code_id})

            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{
                    'price': price_recurring,
                    'discounts': discounts,
                }],
                add_invoice_items=prices_one_time,
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent'],
                coupon=coupon,
                metadata={
                    'referral_code': referral_code_id,
                    'coupon_id': coupon_id,
                }
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
            pass
            # if percent_off:
            #     total_discount_amount += (total_product * int(percent_off)) / 100
            #     total_product = total_product - (total_product * int(percent_off)) / 100
            #
            # if amount_off:
            #     total_discount_amount += int(amount_off)
            #     total_product = total_product - int(amount_off)

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

    return total_product, total_sign_up_fee, total_pro_launch, total_discount_amount


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
        subscription = stripe.Subscription.retrieve(subscription_id, expand=['plan.product'])

        if data_object['billing_reason'] == 'subscription_create':
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id, expand=['invoice', 'source', 'payment_method'])
            stripe.Subscription.modify(
                subscription_id,
                default_payment_method=payment_intent.payment_method
            )
            expiration_date = datetime.fromtimestamp(subscription.current_period_end)
            customer_stripe_id = data_object.customer
            customer = stripe.Customer.retrieve(customer_stripe_id)
            subscription_name = subscription.plan.product.name
            referral_code_rs = None
            if data_object.discount or data_object.total_discount_amounts:
                referral_code_id = subscription.metadata.get('referral_code', None)
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
                    referral_code_rs = data_referral_code
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

                    if company_referral_code and company_referral_code.percent_discount_product:
                        discount_amount = total_amount * company_referral_code.percent_discount_product/100

                    elif company_referral_code and company_referral_code.number_discount_product:
                        discount_amount = company_referral_code.number_discount_product

                    company.credit = round(company.credit + commission_amount, 2)
                    company.save()
                    upcoming_invoice = stripe.Invoice.upcoming(
                        subscription=data_subscription_stripe_company.subscription_id
                    )

                    discount_amount_next_invoice = (upcoming_invoice.subtotal - upcoming_invoice.total) / 100
                    discount_amount = 0
                    if data_sub.discount:
                        discount_amount = data_sub.discount.coupon.amount_off / 100

                    # temp_amount = total_amount - discount_amount_next_invoice
                    temp_amount = upcoming_invoice.total / 100
                    # if company not coupon code when payment first
                    if (not company_referral_code and company.is_automatic_commission_payment and upcoming_invoice.total > 0) or (company_referral_code and is_use_one and company.is_automatic_commission_payment and upcoming_invoice.total > 0):
                        # temp_amount = total_amount - discount_amount
                        create_referral_code = None
                        if company.credit >= temp_amount:
                            company.credit = round(company.credit - temp_amount, 2)
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
                                number_discount_product=total_amount,
                                currency=data_sub.currency,
                                coupon_stripe_id=coupon.id,
                                dealer=None,
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
                                number_discount_product=total_discount_coupon,
                                currency=data_sub.currency,
                                coupon_stripe_id=coupon.id,
                                dealer=None,
                            )
                        company.referral_code_current = create_referral_code
                        company.save()

                    elif company_referral_code and discount_amount_next_invoice < total_amount and not is_use_one and company.is_automatic_commission_payment and temp_amount > 0:
                        if company.credit >= temp_amount and temp_amount > 0:
                            company.credit = round(company.credit - temp_amount, 2)
                            company.save()
                            data_discount = round(temp_amount + discount_amount, 2)
                            coupon = stripe.Coupon.create(
                                percent_off=None,
                                amount_off=int(data_discount * 100),
                                currency=data_sub.currency,
                                duration='once',
                                max_redemptions=1
                            )

                            subscription = stripe.Subscription.modify(
                                data_subscription_stripe_company.subscription_id,
                                discounts=[{"coupon": coupon.id}],
                            )
                        else:
                            total_discount_coupon = company.credit + discount_amount

                            if temp_amount > 0:
                                company.credit = 0
                                company.save()
                                coupon = stripe.Coupon.create(
                                    percent_off=None,
                                    amount_off=int(total_discount_coupon * 100),
                                    currency=data_sub.currency,
                                    duration='once',
                                    max_redemptions=1,
                                )
                                subscription = stripe.Subscription.modify(
                                    data_subscription_stripe_company.subscription_id,
                                    discounts=[{"coupon": coupon.id}],
                                )

                if dealer:
                    data_products = data_object.lines.data
                    commission_amount = 0
                    for product in data_products:
                        product_id = product.price.product
                        data_product = stripe.Product.retrieve(product_id)
                        metadata = data_product.metadata
                        is_launch = metadata.get('is_launch', None)
                        if is_launch == 'True' and not product.price.recurring:
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

                data_company = CompanyBuilder.objects.get(pk=customer.metadata['company'])
                data_company.referral_code_current = referral_code_rs
                data_company.save()

            SubscriptionStripeCompany.objects.create(
                subscription_id=subscription_id,
                customer_stripe=customer_stripe_id,
                company_id=int(customer.metadata['company']),
                subscription_name=subscription_name,
                expiration_date=expiration_date,
                # duration_in_months=data_object.discount.coupon.duration_in_months - 1,
                is_activate=True
            )
            product = stripe.Product.retrieve(subscription.plan.product.id)
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
            pass
    if event_type == 'invoice.upcoming':
        subscription_id = data_object['subscription']
        subscription = stripe.Subscription.retrieve(subscription_id,
                                                       expand=['plan.product'])
        discount_check = data_object.discounts
        customer = stripe.Customer.retrieve(data_object.customer)
        company = CompanyBuilder.objects.get(pk=customer.metadata['company'])
        data_subscription_stripe_company = SubscriptionStripeCompany.objects.filter(company=company).first()
        discount_amount = 0
        for discount in data_object.total_discount_amounts:
            if discount.discount not in discount_check:
                discount_amount += discount.amount / 100
        if not data_object.total_discount_amounts and company.credit > 0:
            total_discount_amount = company.credit
            coupon = stripe.Coupon.create(
                percent_off=None,
                amount_off=int(total_discount_amount * 100),
                currency=subscription.currency,
                duration='once',
                max_redemptions=1
            )
            company.credit = 0
            subscription = stripe.Subscription.modify(
                data_subscription_stripe_company.subscription_id,
                coupon=coupon,
            )
            create_referral_code = ReferralCode.objects.create(
                number_discount_product=total_discount_amount,
                currency=subscription.currency,
                coupon_stripe_id=coupon.id,


            )
            company.referral_code_current = create_referral_code
            company.save()
        if data_object.discounts or data_object.total_discount_amounts:
            is_use_one = False
            coupon_code = company.referral_code_current.coupon_stripe_id
            coupon_company = stripe.Coupon.retrieve(coupon_code)

            if coupon_company.duration == 'once':
                is_use_one = True

            data_referral_code = ReferralCode.objects.filter(coupon_stripe_id=coupon_code).first()
            if company and company.is_automatic_commission_payment:
                total_amount = subscription.plan.amount / 100
                if is_use_one:
                    if company.credit >= total_amount:
                        coupon = stripe.Coupon.create(
                            percent_off=None,
                            amount_off=int((company.credit - total_amount) * 100),
                            currency=subscription.currency,
                            duration='once',
                            max_redemptions=1
                        )
                        company.credit = round(company.credit - total_amount, 2)
                        subscription = stripe.Subscription.modify(
                            data_subscription_stripe_company.subscription_id,
                            coupon=coupon,
                        )
                        create_referral_code = ReferralCode.objects.create(
                            number_discount_product=total_amount,
                            currency=subscription.currency,
                            coupon_stripe_id=coupon.id,
                            dealer=data_referral_code.dealer,

                        )
                        company.referral_code_current = create_referral_code
                        company.save()

                    elif company.credit < total_amount:
                        total_discount_amount = company.credit
                        coupon = stripe.Coupon.create(
                            percent_off=None,
                            amount_off=int(total_discount_amount * 100),
                            currency=subscription.currency,
                            duration='once',
                            max_redemptions=1
                        )
                        company.credit = 0
                        subscription = stripe.Subscription.modify(
                            data_subscription_stripe_company.subscription_id,
                            coupon=coupon,
                        )
                        create_referral_code = ReferralCode.objects.create(
                            number_discount_product=total_discount_amount,
                            currency=subscription.currency,
                            coupon_stripe_id=coupon.id,
                            dealer=data_referral_code.dealer,

                        )
                        company.referral_code_current = create_referral_code
                        company.save()
                else:
                    temp_amount = total_amount - discount_amount
                    if company.credit >= temp_amount and temp_amount > 0:
                        company.credit = round(company.credit - temp_amount, 2)
                        company.save()
                        coupon = stripe.Coupon.create(
                            percent_off=None,
                            amount_off=data_object.total,
                            currency=subscription.currency,
                            duration='once',
                            max_redemptions=1
                        )

                        stripe.Subscription.modify(
                            data_subscription_stripe_company.subscription_id,
                            discounts=[{"coupon": coupon.id}],
                        )
                    elif company.credit > 0 and company.credit < temp_amount:
                        coupon = stripe.Coupon.create(
                            percent_off=None,
                            amount_off=int(company.credit * 100),
                            currency=subscription.currency,
                            duration='once',
                            max_redemptions=1
                        )
                        stripe.Subscription.modify(
                            subscription.id,
                            discounts=[{"coupon": coupon.id}],
                        )
                        company.credit = 0
                        company.save()

            customer_stripe_id = customer.id
            PaymentHistoryStripe.objects.create(
                subscription_id=subscription_id,
                customer_stripe_id=customer_stripe_id,
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
        pass
        # subscription_id = data_object.stripe_id
        # payment_intent = stripe.PaymentIntent.retrieve(data_object.stripe_id, expand=['invoice', 'source', 'payment_method'])
        # subscription = stripe.Subscription.retrieve(payment_intent.invoice.lines.data[0].subscription, expand=['plan.product'])
        # subscription_id = payment_intent.invoice.subscription
        # customer_stripe_id = data_object.customer
        # data_payment_history = PaymentHistoryStripe.objects.filter(
        #     customer_stripe_id=customer_stripe_id
        # )
        # if not data_payment_history:
        #     payload = {
        #         'sub': subscription_id,
        #         'customer': customer_stripe_id,
        #     }
        #     customer = stripe.Customer.retrieve(customer_stripe_id)
        #     jwt_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        #     registration_link = f'{settings.BASE_URL}/register/?link={jwt_token.decode()}'
        #     content = render_to_string('auth/link-create-account.html', {'registration_link': registration_link})
        #     celery_send_mail.delay(f'Create account',
        #                            content, settings.EMAIL_HOST_USER, [customer.email], False)
    elif event.type == 'payment_method.attached':
        pass

    elif event.type == 'charge.failed':
        # payment_intent = stripe.PaymentIntent.retrieve(data_object['payment_intent'],
        #                                                expand=['invoice', 'source', 'payment_method'])
        # subscription = stripe.Subscription.retrieve(payment_intent.invoice.lines.data[0].subscription,
        #                                             expand=['plan.product'])
        #
        # customer = data_object['customer']
        # user = User.objects.get(stripe_customer=customer)
        # company_name = user.company.company_name
        # customer_name = user.username
        # url_login = config('BASE_URL') + '/login/'
        # content = render_to_string('auth/payment-failse.html', {
        #     'subscription_name': subscription.plan.product.name,
        #     'company_name': company_name,
        #     'customer_name': customer_name,
        #     'url_login': url_login
        # })
        # celery_send_mail.delay(f'Stripe Fail Payment - this is a test',
        #                        content, settings.EMAIL_HOST_USER, [user.email], False)
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


@api_view(['GET'])
def get_data_dealer(request, period):
    if request.method == 'GET' and request.user.is_authenticated:
        dealer_info = DealerInformation.objects.get(user=request.user)
        total_amount = 0
        total_user = 0
        end_date = datetime.now()
        start_date = None
        if period == WEEK:
            start_date = end_date - timedelta(days=7)

        elif period == MONTH:
            start_date = end_date - timedelta(days=30)

        elif period == YEAR:
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