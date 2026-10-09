from django.urls import path

from . import views

urlpatterns = [
    path("webhooks/orders", views.OrderWebhookView.as_view(), name="webhook-orders"),
]
