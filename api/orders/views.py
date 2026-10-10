import json
import logging

from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from . import constants
from .filters import filter_orders
from .models import Order
from .providers import ingest
from .providers.base import InvalidOrderPayload, OrderLookupError
from .serializers import OrderDetailSerializer, OrderListSerializer

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class OrderWebhookView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request) -> Response:
        try:
            raw_body = request.body
        except RequestDataTooBig:
            return self._error(
                "Request body is too large.", status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )
        # A provider must always get JSON back, never Django's HTML error page.
        try:
            return self._handle(raw_body, request.headers)
        except Exception:
            logger.exception("Webhook handling failed")
            return self._error("internal error", status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle(self, raw_body: bytes, headers) -> Response:
        payload = self._parse_json_object(raw_body)
        if payload is None:
            return self._error("Body must be a JSON object.", status.HTTP_400_BAD_REQUEST)

        provider = ingest.find_provider(payload)
        if provider is None:
            return self._error("Unknown payload shape.", status.HTTP_400_BAD_REQUEST)

        if not provider.authenticate(raw_body, headers):
            return self._error("Authentication failed.", status.HTTP_401_UNAUTHORIZED)

        try:
            ignored = provider.ignored_event(payload)
            if ignored is not None:
                logger.info("Ignored webhook event %s", ignored)
                reply = provider.ignored_reply(ignored)
                return Response(reply.body, status=reply.status)
            order = ingest.ingest(provider, payload)
        except InvalidOrderPayload as error:
            reply = provider.rejected_reply(str(error))
        except OrderLookupError as error:
            return self._error(str(error), status.HTTP_502_BAD_GATEWAY)
        else:
            reply = provider.accepted_reply(order.id)
        return Response(reply.body, status=reply.status)

    @staticmethod
    def _parse_json_object(raw_body: bytes) -> dict | None:
        try:
            payload = json.loads(raw_body)
        except (ValueError, RecursionError):
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _error(message: str, status_code: int) -> Response:
        return Response({"detail": message}, status=status_code)


class OrderPagination(PageNumberPagination):
    def get_page_size(self, request) -> int:
        return settings.PAGE_SIZE

    # A page past the end (for example after orders moved out of a status
    # filter) answers with the last page instead of a 404, and a page that
    # is not a number answers with the first. The reply names the page it
    # holds, so the client can correct its address.
    def paginate_queryset(self, queryset, request, view=None) -> list:
        paginator = self.django_paginator_class(queryset, self.get_page_size(request))
        self.page = paginator.get_page(request.query_params.get(self.page_query_param))
        self.request = request
        return list(self.page)

    def get_paginated_response(self, data) -> Response:
        response = super().get_paginated_response(data)
        response.data[constants.PAGE_FIELD] = self.page.number
        return response


class OrderListView(ListAPIView):
    serializer_class = OrderListSerializer
    pagination_class = OrderPagination

    def get_queryset(self):
        return filter_orders(Order.objects.all(), self.request.query_params)


class OrderDetailView(RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderDetailSerializer


class OrderStatusView(APIView):
    def patch(self, request, pk: int) -> Response:
        expected_status = self._expected_status(request.data)
        with transaction.atomic():
            order = get_object_or_404(Order.objects.select_for_update(), pk=pk)
            if expected_status is not None and expected_status != order.status:
                return Response(
                    OrderDetailSerializer(order).data, status=status.HTTP_409_CONFLICT
                )
            next_status = order.next_status()
            if next_status is None:
                return Response(
                    {"detail": f"Order is already {order.status}."},
                    status=status.HTTP_409_CONFLICT,
                )
            order.status = next_status
            order.save(update_fields=["status", "updated_at"])
        return Response(OrderDetailSerializer(order).data)

    @staticmethod
    def _expected_status(data) -> str | None:
        if not isinstance(data, dict):
            raise ValidationError("The body must be a JSON object.")
        expected_status = data.get(constants.EXPECTED_STATUS_FIELD)
        if expected_status is not None and expected_status not in constants.STATUS_ORDER:
            raise ValidationError({constants.EXPECTED_STATUS_FIELD: "Unknown status."})
        return expected_status
