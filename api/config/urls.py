from django.conf import settings
from django.urls import include, path

urlpatterns = [
    path("api/", include("orders.urls")),
]

if settings.DEMO_ENABLED:
    urlpatterns.append(path("demo/", include("demo.urls")))
