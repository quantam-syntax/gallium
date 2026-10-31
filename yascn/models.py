import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .validators import validate_password


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        if password is None:
            raise ValueError("Password is required.")
        validate_password(password)
        user = self.model(email=email.strip().lower(), **extra_fields)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "admin")
        extra_fields.setdefault("is_superuser", True)
        if extra_fields["role"] != "admin" or extra_fields["is_superuser"] is not True:
            raise ValueError("Superusers must have the admin role and is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        STAFF = "staff", "Staff"
        CUSTOMER = "customer", "Customer"

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CUSTOMER)
    is_active = models.BooleanField(default=True)
    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        constraints = [models.UniqueConstraint(Lower("email"), name="yascn_user_email_ci")]

    @property
    def is_staff(self):
        return self.role in (self.Role.ADMIN, self.Role.STAFF)

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class Tax(models.Model):
    name = models.CharField(max_length=200)
    rate_bps = models.PositiveIntegerField(validators=[MaxValueValidator(10000)])
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(rate_bps__lte=10000), name="yascn_tax_rate")]


class Product(models.Model):
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=80)
    sale_price_paise = models.PositiveBigIntegerField()
    cost_price_paise = models.PositiveBigIntegerField(default=0)
    notes = models.TextField(blank=True)
    tax = models.ForeignKey(Tax, null=True, blank=True, on_delete=models.PROTECT)
    active = models.BooleanField(default=True)


class Variant(models.Model):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    price_delta_paise = models.PositiveBigIntegerField()


class Plan(models.Model):
    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    name = models.CharField(max_length=200)
    base_price_paise = models.PositiveBigIntegerField()
    tax = models.ForeignKey(Tax, null=True, blank=True, on_delete=models.PROTECT)
    frequency = models.CharField(max_length=10, choices=Frequency.choices)
    minimum_quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    available_from = models.DateField(null=True, blank=True)
    available_to = models.DateField(null=True, blank=True)
    auto_close = models.BooleanField(default=False)
    allow_pause = models.BooleanField(default=True)
    allow_renew = models.BooleanField(default=True)
    allow_cancel = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(minimum_quantity__gte=1), name="yascn_plan_min_qty"),
            models.CheckConstraint(condition=(models.Q(available_from__isnull=True) | models.Q(available_to__isnull=True)
                | models.Q(available_to__gte=models.F("available_from"))), name="yascn_plan_dates"),
        ]


class Discount(models.Model):
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=[("fixed", "Fixed"), ("percent", "Percent")])
    value = models.PositiveBigIntegerField()
    scope = models.CharField(max_length=15, choices=[("product", "Product"), ("subscription", "Subscription")])
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.PROTECT)
    min_purchase_paise = models.PositiveBigIntegerField(default=0)
    min_quantity = models.PositiveIntegerField(default=0)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~models.Q(kind="percent") | models.Q(value__lte=10000), name="yascn_discount_rate"),
            models.CheckConstraint(condition=(models.Q(scope="product", product__isnull=False)
                | models.Q(scope="subscription", product__isnull=True)), name="yascn_discount_scope"),
            models.CheckConstraint(condition=(models.Q(starts_on__isnull=True) | models.Q(ends_on__isnull=True)
                | models.Q(ends_on__gte=models.F("starts_on"))), name="yascn_discount_dates"),
        ]


class QuotationTemplate(models.Model):
    name = models.CharField(max_length=200)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    valid_days = models.PositiveIntegerField(default=14, validators=[MinValueValidator(1)])

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(valid_days__gte=1), name="yascn_template_days")]


class TemplateLine(models.Model):
    template = models.ForeignKey(QuotationTemplate, related_name="lines", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(Variant, null=True, blank=True, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price_paise = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gte=1), name="yascn_template_line_qty")]


def subscription_number():
    # UUID-backed numbering avoids max(id)+1 races and a temporary blank number.
    return "SUB-" + uuid.uuid4().hex.upper()


class Subscription(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        QUOTATION = "quotation", "Quotation"
        CONFIRMED = "confirmed", "Confirmed"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        EXPIRED = "expired", "Expired"
        CLOSED = "closed", "Closed"

    number = models.CharField(max_length=40, unique=True, default=subscription_number, editable=False)
    customer = models.ForeignKey(User, related_name="subscriptions", on_delete=models.PROTECT)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    start_date = models.DateField()
    expiry_date = models.DateField()
    quote_expires_at = models.DateTimeField(null=True, blank=True)
    payment_terms_days = models.PositiveIntegerField(default=14)
    next_bill_date = models.DateField()
    subscription_discount = models.ForeignKey(Discount, null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        indexes = [models.Index(fields=["status", "next_bill_date"], name="yascn_due_idx")]
        constraints = [
            models.CheckConstraint(condition=models.Q(expiry_date__gt=models.F("start_date")), name="yascn_subscription_dates"),
            models.CheckConstraint(condition=models.Q(next_bill_date__gte=models.F("start_date")), name="yascn_subscription_cursor"),
        ]

    @property
    def permitted_actions(self):
        # Phase 1 exposes only the core staff quotation-to-active path.
        now = timezone.now()
        if self.quote_expires_at and now >= self.quote_expires_at and self.status in ("draft", "quotation", "confirmed"):
            return []
        if self.expiry_date <= timezone.localdate():
            return []
        return {"draft": ["quote"], "quotation": ["confirm"], "confirmed": ["activate"]}.get(self.status, [])


class SubscriptionLine(models.Model):
    subscription = models.ForeignKey(Subscription, related_name="lines", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(Variant, null=True, blank=True, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price_paise = models.PositiveBigIntegerField()
    tax = models.ForeignKey(Tax, null=True, blank=True, on_delete=models.PROTECT)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gte=1), name="yascn_sub_line_qty")]
