from django.utils import timezone
from rest_framework import serializers

from .models import Invoice, Payment


class InvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    paid_paise = serializers.IntegerField(read_only=True)
    balance_paise = serializers.IntegerField(read_only=True)
    is_overdue = serializers.SerializerMethodField()
    is_partially_paid = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "number",
            "subscription_id",
            "customer_id",
            "customer_name",
            "period_start",
            "period_end",
            "revision",
            "issued_on",
            "due_on",
            "status",
            "subtotal_paise",
            "discount_paise",
            "tax_paise",
            "total_paise",
            "paid_paise",
            "balance_paise",
            "is_overdue",
            "is_partially_paid",
            "snapshot",
            "sent_at",
        ]
        read_only_fields = fields

    def get_customer_name(self, obj):
        return (
            getattr(obj.customer, "full_name", "")
            or getattr(obj.customer, "get_full_name", lambda: "")()
            or obj.customer.email
        )

    def get_is_overdue(self, obj):
        return (
            obj.status != "cancelled"
            and obj.balance_paise > 0
            and obj.due_on < timezone.localdate()
        )

    def get_is_partially_paid(self, obj):
        return obj.status != "cancelled" and 0 < obj.paid_paise < obj.total_paise


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "invoice_id",
            "method",
            "amount_paise",
            "paid_on",
            "note",
            "created_by_id",
        ]
        read_only_fields = ["id", "invoice_id", "created_by_id"]
        extra_kwargs = {
            "amount_paise": {"min_value": 1},
            "method": {"allow_blank": False},
        }


class DashboardFilterSerializer(serializers.Serializer):
    def get_fields(self):
        return {
            "from": serializers.DateField(required=False),
            "to": serializers.DateField(required=False),
        }

    def validate(self, attrs):
        if attrs.get("from") and attrs.get("to") and attrs["from"] > attrs["to"]:
            raise serializers.ValidationError({"to": "Must be on or after from."})
        return attrs
