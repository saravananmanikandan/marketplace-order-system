import hmac

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from orders import constants
from orders.providers.base import InvalidOrderPayload, OrderLookupError

from .clients import StagedOrderClient


class MockUberOrderView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, order_id: str) -> Response:
        if not self._has_valid_token(request.headers.get(constants.AUTHORIZATION_HEADER, "")):
            return Response({"detail": "Unauthorized."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            order = StagedOrderClient().get_order(order_id)
        except InvalidOrderPayload:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except OrderLookupError as error:
            return Response({"detail": str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(order)

    @staticmethod
    def _has_valid_token(provided: str) -> bool:
        if not settings.UBER_ACCESS_TOKEN:
            return False
        expected = constants.BEARER_PREFIX + settings.UBER_ACCESS_TOKEN
        return hmac.compare_digest(expected.encode(), provided.encode())
