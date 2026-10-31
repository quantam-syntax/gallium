from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import (User, Tax, Product, Variant, Plan, Discount, QuotationTemplate,
                     TemplateLine, Subscription, SubscriptionLine)
from .validators import validate_password


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "company_name", "role"]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, validators=[validate_password])

    class Meta:
        model = User
        fields = ["email", "password", "full_name", "company_name", "role"]

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_role(self, value):
        actor = self.context["request"].user
        if value != "customer" and not (actor.is_authenticated and actor.role == "admin"):
            raise serializers.ValidationError("Only an admin may create staff or admin accounts.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


def validate_dates(attrs, instance, first, last):
    start = attrs.get(first, getattr(instance, first, None))
    end = attrs.get(last, getattr(instance, last, None))
    if start and end and end < start:
        raise serializers.ValidationError({last: "Must be on or after the start date."})
    return attrs


class TaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tax
        fields = ["id", "name", "rate_bps", "active"]


class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = ["id", "name", "price_delta_paise"]


class ProductSerializer(serializers.ModelSerializer):
    tax_id = serializers.PrimaryKeyRelatedField(source="tax", queryset=Tax.objects.all(), allow_null=True, required=False)
    variants = VariantSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = ["id", "name", "type", "sale_price_paise", "cost_price_paise", "notes", "tax_id", "active", "variants"]

    @transaction.atomic
    def create(self, validated_data):
        variants = validated_data.pop("variants", [])
        product = super().create(validated_data)
        for variant in variants:
            Variant.objects.create(product=product, **variant)
        return product

    def validate(self, attrs):
        if self.instance and "variants" in attrs:
            raise serializers.ValidationError({"variants": "Use the product variant endpoint to edit existing variants."})
        return attrs


class PlanSerializer(serializers.ModelSerializer):
    tax_id = serializers.PrimaryKeyRelatedField(source="tax", queryset=Tax.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Plan
        fields = ["id", "name", "base_price_paise", "tax_id", "frequency", "minimum_quantity", "available_from",
                  "available_to", "auto_close", "allow_pause", "allow_renew", "allow_cancel"]

    def validate(self, attrs):
        return validate_dates(attrs, self.instance, "available_from", "available_to")


class DiscountSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(source="product", queryset=Product.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Discount
        fields = ["id", "name", "kind", "value", "scope", "product_id", "min_purchase_paise", "min_quantity",
                  "starts_on", "ends_on", "usage_limit", "used_count", "active"]
        read_only_fields = ["used_count"]

    def validate(self, attrs):
        validate_dates(attrs, self.instance, "starts_on", "ends_on")
        def current(key, default=None):
            return attrs.get(key, getattr(self.instance, key, default))
        if current("kind") == "percent" and current("value", 0) > 10000:
            raise serializers.ValidationError({"value": "Percentage must not exceed 10000 basis points."})
        if (current("scope") == "product") != (current("product") is not None):
            raise serializers.ValidationError({"product_id": "Required only for product discounts."})
        return attrs


class LineSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(source="product", queryset=Product.objects.filter(active=True))
    variant_id = serializers.PrimaryKeyRelatedField(source="variant", queryset=Variant.objects.all(), allow_null=True, required=False)
    unit_price_paise = serializers.IntegerField(min_value=0, required=False)

    class Meta:
        model = TemplateLine
        fields = ["id", "product_id", "variant_id", "quantity", "unit_price_paise"]

    def validate(self, attrs):
        missing = {key: "Required when replacing lines." for key in ("product", "quantity") if key not in attrs}
        if missing:
            raise serializers.ValidationError({"product_id" if key == "product" else key: value for key, value in missing.items()})
        product, variant = attrs["product"], attrs.get("variant")
        if variant and variant.product_id != product.id:
            raise serializers.ValidationError({"variant_id": "Variant must belong to the selected product."})
        # Caller-supplied prices are already effective, including the surcharge.
        attrs.setdefault("unit_price_paise", product.sale_price_paise + (variant.price_delta_paise if variant else 0))
        return attrs


class SubscriptionLineSerializer(LineSerializer):
    tax_id = serializers.PrimaryKeyRelatedField(source="tax", queryset=Tax.objects.all(), allow_null=True, required=False)

    class Meta(LineSerializer.Meta):
        model = SubscriptionLine
        fields = LineSerializer.Meta.fields + ["tax_id", "active"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs.setdefault("tax", attrs["product"].tax)
        return attrs


def check_quantity(plan, lines):
    quantity = sum(line["quantity"] for line in lines if line.get("active", True))
    if quantity < plan.minimum_quantity:
        raise serializers.ValidationError({"lines": f"Total active quantity must be at least {plan.minimum_quantity}."})


class TemplateSerializer(serializers.ModelSerializer):
    plan_id = serializers.PrimaryKeyRelatedField(source="plan", queryset=Plan.objects.all())
    lines = LineSerializer(many=True, allow_empty=False)

    class Meta:
        model = QuotationTemplate
        fields = ["id", "name", "plan_id", "valid_days", "lines"]

    def validate(self, attrs):
        plan = attrs.get("plan", getattr(self.instance, "plan", None))
        lines = attrs.get("lines")
        if lines is None and self.instance:
            lines = list(self.instance.lines.values("quantity"))
        check_quantity(plan, lines)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        lines = validated_data.pop("lines")
        template = super().create(validated_data)
        for line in lines:
            TemplateLine.objects.create(template=template, **line)
        return template

    @transaction.atomic
    def update(self, instance, validated_data):
        lines = validated_data.pop("lines", None)
        instance = super().update(instance, validated_data)
        if lines is not None:
            instance.lines.all().delete()
            for line in lines:
                TemplateLine.objects.create(template=instance, **line)
        return instance


class SubscriptionSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role="customer", is_active=True))
    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all(), required=False)
    lines = SubscriptionLineSerializer(many=True, required=False, allow_empty=False)
    template_id = serializers.PrimaryKeyRelatedField(source="template", queryset=QuotationTemplate.objects.all(), write_only=True, required=False)
    subscription_discount_id = serializers.PrimaryKeyRelatedField(source="subscription_discount",
        queryset=Discount.objects.filter(scope="subscription", active=True), allow_null=True, required=False)
    permitted_actions = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ["id", "number", "customer", "plan", "status", "start_date", "expiry_date", "quote_expires_at",
                  "payment_terms_days", "next_bill_date", "subscription_discount_id", "lines", "permitted_actions", "template_id"]
        read_only_fields = ["number", "status", "next_bill_date"]

    def get_permitted_actions(self, obj):
        if self.context["request"].user.role == "customer":
            return []
        return obj.permitted_actions

    def validate(self, attrs):
        for key in ("number", "status", "next_bill_date"):
            if key in self.initial_data:
                raise serializers.ValidationError({key: "Managed by the server; use transition actions for status."})
        template = attrs.get("template")
        if self.instance and template:
            raise serializers.ValidationError({"template_id": "Templates may only be applied on creation."})
        if template:
            if "lines" in attrs or ("plan" in attrs and attrs["plan"] != template.plan):
                raise serializers.ValidationError({"template_id": "Use the template's plan and lines without overrides."})
            attrs["plan"] = template.plan
            attrs["lines"] = [dict(product=line.product, variant=line.variant, quantity=line.quantity,
                unit_price_paise=line.unit_price_paise, tax=line.product.tax, active=True)
                for line in template.lines.select_related("product__tax", "variant").all()]
        plan = attrs.get("plan", getattr(self.instance, "plan", None))
        if plan is None:
            raise serializers.ValidationError({"plan": "Supply a plan or template_id."})
        today = timezone.localdate()
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("expiry_date", getattr(self.instance, "expiry_date", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"expiry_date": "Must be after start_date (exclusive expiry)."})
        if ((plan.available_from and today < plan.available_from)
                or (plan.available_to and today > plan.available_to)):
            raise serializers.ValidationError({"plan": "Plan is not available for new sign-ups today."})
        if not self.instance and "lines" not in attrs:
            raise serializers.ValidationError({"lines": "Supply lines or template_id."})
        lines = attrs.get("lines")
        if lines is None and self.instance:
            lines = list(self.instance.lines.values("quantity", "active"))
        check_quantity(plan, lines)
        quote_end = attrs.get("quote_expires_at")
        if quote_end and quote_end <= timezone.now():
            raise serializers.ValidationError({"quote_expires_at": "Must be in the future."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        template = validated_data.pop("template", None)
        lines = validated_data.pop("lines")
        if template:
            end_date = timezone.localdate() + timedelta(days=template.valid_days)
            validated_data.setdefault("quote_expires_at", timezone.make_aware(datetime.combine(end_date, time.min)))
        validated_data["next_bill_date"] = validated_data["start_date"]
        subscription = super().create(validated_data)
        for line in lines:
            SubscriptionLine.objects.create(subscription=subscription, **line)
        return subscription

    @transaction.atomic
    def update(self, instance, validated_data):
        lines = validated_data.pop("lines", None)
        if "start_date" in validated_data:
            validated_data["next_bill_date"] = validated_data["start_date"]
        instance = super().update(instance, validated_data)
        if lines is not None:
            instance.lines.all().delete()
            for line in lines:
                SubscriptionLine.objects.create(subscription=instance, **line)
        return instance
