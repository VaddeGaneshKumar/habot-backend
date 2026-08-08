from django.contrib import admin
from .models import Parent, LSAProfile, BookingRequest, Payment


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'email', 'phone', 'created_at']
    search_fields = ['full_name', 'email']


@admin.register(LSAProfile)
class LSAProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'email', 'skills', 'hourly_rate', 'is_available']
    list_filter = ['is_available']
    search_fields = ['full_name', 'email']


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'parent', 'lsa', 'session_start', 'session_end', 'status']
    list_filter = ['status']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'booking', 'amount', 'currency', 'status', 'gateway_reference']
    list_filter = ['status']
