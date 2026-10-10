from django.urls import path

from orders import constants

from . import views

MOCK_UBER_ORDER_ROUTE = "mock/uber" + constants.UBER_GET_ORDER_PATH.replace(
    "{order_id}", "<str:order_id>"
)

urlpatterns = [
    path(MOCK_UBER_ORDER_ROUTE, views.MockUberOrderView.as_view(), name="demo-mock-uber-get-order"),
    path("api/config", views.SimulatorConfigView.as_view(), name="demo-simulator-config"),
    path("api/send", views.SimulatorSendView.as_view(), name="demo-simulator-send"),
    path("api/curl", views.SimulatorCurlView.as_view(), name="demo-simulator-curl"),
]
