import json

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .providers import ingest
from .providers.base import InvalidPayloadError, OrderLookupError


@method_decorator(csrf_exempt, name="dispatch")
class OrderWebhookView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request) -> Response:
        raw_body = request.body
        payload = self._parse_json_object(raw_body)
        if payload is None:
            return self._error("Body must be a JSON object.", status.HTTP_400_BAD_REQUEST)

        provider = ingest.find_provider(payload)
        if provider is None:
            return self._error("Unknown payload shape.", status.HTTP_400_BAD_REQUEST)

        if not provider.authenticate(raw_body, request.headers):
            return self._error("Authentication failed.", status.HTTP_401_UNAUTHORIZED)

        try:
            ingest.ingest(provider, payload)
        except InvalidPayloadError as error:
            return self._error(str(error), status.HTTP_400_BAD_REQUEST)
        except OrderLookupError as error:
            return self._error(str(error), status.HTTP_502_BAD_GATEWAY)
        return Response(status=status.HTTP_200_OK)

    @staticmethod
    def _parse_json_object(raw_body: bytes) -> dict | None:
        try:
            payload = json.loads(raw_body)
        except ValueError:
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _error(message: str, status_code: int) -> Response:
        return Response({"detail": message}, status=status_code)
