from django.db.models import F, Q, QuerySet
from django.db.models.expressions import OrderBy
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


def resolve_ordering(requested: str | None) -> list[OrderBy]:
    requested = requested or ""
    descending = requested.startswith(constants.DESCENDING_PREFIX)
    key = requested.removeprefix(constants.DESCENDING_PREFIX)
    if key not in constants.ORDERING_EXPRESSIONS:
        return resolve_ordering(constants.DEFAULT_ORDERING)
    expressions = [constants.ORDERING_EXPRESSIONS[key], F("id")]
    return [expression.desc() if descending else expression.asc() for expression in expressions]
