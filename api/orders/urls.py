from django.urls import path

from . import views

urlpatterns = [
    path("webhooks/orders", views.OrderWebhookView.as_view(), name="webhook-orders"),
    path("orders", views.OrderListView.as_view(), name="order-list"),
    path("orders/<int:pk>", views.OrderDetailView.as_view(), name="order-detail"),
    path("orders/<int:pk>/status", views.OrderStatusView.as_view(), name="order-status"),
]
