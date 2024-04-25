from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

from api.models import CompanyBuilder


class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=100, blank=True)
    stripe_product_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Price(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_product')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    stripe_price_id = models.CharField(max_length=100, blank=True)
    is_activate = models.BooleanField(default=False, blank=True)


class PaymentHistoryStripe(models.Model):
    class Meta:
        db_table = 'payment_history_stripe'
    date = models.DateTimeField(auto_now_add=True)
    subscription_id = models.CharField(max_length=100, blank=True)
    customer_stripe_id = models.CharField(max_length=100, blank=True)
    payment_method_id = models.CharField(max_length=100, blank=True)
    subscription_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=100, blank=True)
    card_number = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    payment_day = models.IntegerField(blank=True, null=True)
    # is_activate = models.BooleanField(default=False, blank=True)


class ReferralCode(models.Model):
    title = models.CharField(max_length=100, blank=True)
    code = models.CharField(max_length=200, blank=True)
    description = models.CharField(max_length=200, blank=True)
    number_discount_sign_up = models.FloatField(blank=True, null=True, verbose_name='Sign-up Fee Discount ($)')
    currency = models.CharField(max_length=100, blank=True, default='USD')
    percent_discount_sign_up = models.IntegerField(blank=True, null=True, verbose_name='Sign-up Fee Discount (%)')
    number_discount_product = models.FloatField(blank=True, null=True, verbose_name='Subscription Discount ($)')
    percent_discount_product = models.IntegerField(blank=True, null=True, verbose_name='Subscription Discount (%)')
    currency_product = models.CharField(max_length=100, blank=True, default='USD')
    number_discount_pro_launch = models.FloatField(blank=True, null=True, verbose_name='Pro-Launch Discount ($)')
    percent_discount_pro_launch = models.IntegerField(blank=True, null=True, verbose_name='Pro-Launch Discount (%)')
    currency_pro_launch = models.CharField(max_length=100, blank=True)
    monthly_discounts = models.IntegerField(blank=True, null=True)
    products = models.ManyToManyField(Product, related_name='product_apply', blank=True)
    number_of_uses = models.IntegerField(blank=True, null=True)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    coupon_stripe_id = models.CharField(max_length=100, blank=True)
    dealer = models.ForeignKey('DealerInformation', on_delete=models.SET_NULL, related_name='referral_code_dealer',null=True, blank=True)
    company = models.ForeignKey(CompanyBuilder, on_delete=models.SET_NULL, related_name='code_company',null=True, blank=True)
    is_activate = models.BooleanField(blank=True, null=True)
    promotion_code_id = models.CharField(max_length=100, blank=True)

    # def clean(self):
    #     if self.code:
    #         if ReferralCode.objects.filter(code=self.code).exists():
    #             raise ValidationError({'code': 'This referral code already exists.'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class DealerInformation(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, related_name='user_dealer',null=True, blank=True)
    total_bonus_commissions = models.IntegerField(blank=True, null=True, default=0)
    created_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class DealerCompany(models.Model):
    dealer = models.ForeignKey(DealerInformation, on_delete=models.SET_NULL, related_name='dealer_company',null=True, blank=True)
    company = models.ForeignKey(CompanyBuilder, on_delete=models.CASCADE, related_name='%(class)s_company_builder', null=True, blank=True)
    referral_code = models.ForeignKey(ReferralCode, on_delete=models.CASCADE, related_name='%(class)s_referral_code', null=True, blank=True)
    is_activate = models.BooleanField(default=True, blank=True)
    bonus_commissions = models.IntegerField(blank=True, null=True, default=0)
    created_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class CouponCode(models.Model):
    title = models.CharField(max_length=100, blank=True)
    code = models.CharField(max_length=200, blank=True)
    description = models.CharField(max_length=200, blank=True)
    number_discount_sign_up = models.IntegerField(blank=True, null=True, verbose_name='Sign-up Fee Discount ($)')
    currency = models.CharField(max_length=100, blank=True, default='USD')
    percent_discount_sign_up = models.IntegerField(blank=True, null=True, verbose_name='Sign-up Fee Discount (%)')
    number_discount_product = models.IntegerField(blank=True, null=True, verbose_name='Subscription Discount ($)')
    percent_discount_product = models.IntegerField(blank=True, null=True, verbose_name='Subscription Discount (%)')
    currency_product = models.CharField(max_length=100, blank=True, default='USD')
    number_discount_pro_launch = models.IntegerField(blank=True, null=True, verbose_name='Pro-Launch Discount ($)')
    percent_discount_pro_launch = models.IntegerField(blank=True, null=True, verbose_name='Pro-Launch Discount (%)')
    currency_pro_launch = models.CharField(max_length=100, blank=True, default='USD')
    monthly_discounts = models.IntegerField(blank=True, null=True)
    products = models.ManyToManyField(Product, related_name='product_coupon_apply', blank=True)
    number_of_uses = models.IntegerField(blank=True, null=True)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    coupon_stripe_id = models.CharField(max_length=100, blank=True)

    # def clean(self):
    #     if self.code:
    #         if CouponCode.objects.filter(code=self.code).exists():
    #             raise ValidationError({'code': 'This coupon code already exists.'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class ConfigReferralCode(models.Model):
    title = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=200, blank=True)
    default_percent_discount_sign_up = models.IntegerField(blank=True, null=True)
    default_percent_discount_product = models.IntegerField(blank=True, null=True)
    default_percent_discount_pro_launch = models.IntegerField(blank=True, null=True)
