from django.contrib import admin
from django.urls import path
from bookings.views import BookingCreateView, LSASearchView, PaymentWebhookView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/bookings/', BookingCreateView.as_view(), name='booking-create'),
    path('api/v1/lsas/search/', LSASearchView.as_view(), name='lsa-search'),
    path('api/payments/webhook/', PaymentWebhookView.as_view(), name='payment-webhook'),
]
