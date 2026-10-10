from rest_framework import serializers

from .models import Order


class OrderListSerializer(serializers.ModelSerializer):
    customer = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "provider",
            "external_order_id",
            "status",
            "customer",
            "total_cents",
            "currency",
            "created_at",
            "updated_at",
        ]

    def get_customer(self, order: Order) -> dict[str, str]:
        return {
            "name": order.customer_name,
            "phone": order.customer_phone,
            "phone_code": order.customer_phone_code,
        }


class OrderDetailSerializer(OrderListSerializer):
    class Meta(OrderListSerializer.Meta):
        fields = OrderListSerializer.Meta.fields + ["line_items", "raw_payload"]
