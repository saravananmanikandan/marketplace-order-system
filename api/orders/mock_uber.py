import hmac

from django.conf import settings
from django.urls import path
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import constants
from .providers.base import InvalidOrderPayload, OrderLookupError
from .providers.uber import official_order_for, require_resource_id


class MockUberOrderView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, order_id: str) -> Response:
        if not self._has_valid_token(request.headers.get(constants.AUTHORIZATION_HEADER, "")):
            return Response({"detail": "Unauthorized."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            order = official_order_for(
                require_resource_id(order_id), settings.UBER_GET_ORDER_FIXTURE
            )
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


urlpatterns = [
    path(
        constants.UBER_GET_ORDER_PATH.lstrip("/").replace("{order_id}", "<str:order_id>"),
        MockUberOrderView.as_view(),
        name="mock-uber-get-order",
    ),
]
