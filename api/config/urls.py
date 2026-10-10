from django.conf import settings
from django.urls import include, path

urlpatterns = [
    path("api/", include("orders.urls")),
]

if settings.MOCK_UBER_ENABLED:
    urlpatterns.append(path("mock/uber/", include("orders.mock_uber")))
