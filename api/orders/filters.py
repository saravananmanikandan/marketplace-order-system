from django.db.models import Q, QuerySet
from django.http import QueryDict

from . import constants


def filter_orders(queryset: QuerySet, params: QueryDict) -> QuerySet:
    provider = params.get("provider")
    if provider:
        queryset = queryset.filter(provider=provider)

    status = params.get("status")
    if status:
        queryset = queryset.filter(status=status)

    search = params.get("search", "").strip()
    if search:
        queryset = queryset.filter(
            Q(customer_name__icontains=search) | Q(external_order_id__icontains=search)
        )

    return queryset.order_by(*resolve_ordering(params.get("ordering")))


def resolve_ordering(requested: str | None) -> tuple[str, str]:
    ordering = (
        requested
        if requested in constants.ORDERING_CHOICES
        else constants.ORDERING_NEWEST_FIRST
    )
    tiebreaker = "-id" if ordering.startswith("-") else "id"
    return ordering, tiebreaker
