from django.db import models
from django.utils import timezone

from . import constants


class Order(models.Model):
    provider = models.CharField(max_length=32, choices=constants.PROVIDER_CHOICES)
    external_order_id = models.CharField(max_length=constants.MAX_EXTERNAL_ID_LENGTH)
    status = models.CharField(
        max_length=16, choices=constants.STATUS_CHOICES, default=constants.STATUS_NEW
    )
    customer_name = models.CharField(
        max_length=constants.MAX_CUSTOMER_NAME_LENGTH, blank=True
    )
    customer_phone = models.CharField(
        max_length=constants.MAX_CUSTOMER_PHONE_LENGTH, blank=True
    )
    customer_phone_code = models.CharField(
        max_length=constants.MAX_CUSTOMER_PHONE_CODE_LENGTH, blank=True, default=""
    )
    line_items = models.JSONField(default=list)
    total_cents = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=constants.CURRENCY_CODE_LENGTH)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    raw_payload = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_order_id"],
                name="unique_order_per_provider",
            )
        ]
        indexes = [
            models.Index(fields=["status"], name="order_status_idx"),
            models.Index(fields=["created_at"], name="order_created_at_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.external_order_id}"

    @property
    def is_terminal(self) -> bool:
        return self.status in constants.TERMINAL_STATUSES

    def next_status(self) -> str | None:
        if self.is_terminal:
            return None
        position = constants.STATUS_PROGRESSION.index(self.status)
        return constants.STATUS_PROGRESSION[position + 1]
