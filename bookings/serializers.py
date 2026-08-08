from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Parent, LSAProfile, BookingRequest, Payment


class ParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = ['id', 'full_name', 'email', 'phone', 'created_at']
        read_only_fields = ['id', 'created_at']


class LSAProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LSAProfile
        fields = ['id', 'full_name', 'email', 'skills', 'hourly_rate', 'is_available', 'bio']
        read_only_fields = ['id']


class BookingRequestSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.full_name', read_only=True)
    lsa_name = serializers.CharField(source='lsa.full_name', read_only=True)

    class Meta:
        model = BookingRequest
        fields = ['id', 'parent', 'lsa', 'parent_name', 'lsa_name',
                  'session_start', 'session_end', 'status', 'notes', 'created_at']
        read_only_fields = ['id', 'status', 'created_at', 'parent_name', 'lsa_name']

    def validate(self, data):
        if data.get('session_start') and data.get('session_end'):
            if data['session_start'] >= data['session_end']:
                raise serializers.ValidationError("session_end must be after session_start.")

            # Check overlapping bookings
            if data.get('lsa'):
                overlapping = BookingRequest.objects.filter(
                    lsa=data['lsa'],
                    status__in=['pending', 'confirmed'],
                    session_start__lt=data['session_end'],
                    session_end__gt=data['session_start'],
                )
                if overlapping.exists():
                    raise serializers.ValidationError(
                        "This LSA already has a booking overlapping this time slot. Double-booking prevented.")
        return data


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'booking', 'amount', 'currency', 'status', 'gateway_reference', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']
