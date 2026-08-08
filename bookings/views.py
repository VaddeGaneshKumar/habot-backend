import logging
import json
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Parent, LSAProfile, BookingRequest, Payment
from .serializers import BookingRequestSerializer, LSAProfileSerializer, PaymentSerializer

logger = logging.getLogger(__name__)
MOCK_PAYMENT_GATEWAY_URL = "https://httpbin.org/post"


class BookingCreateView(APIView):
    """POST /api/v1/bookings/ — Create booking with overlap prevention"""

    def post(self, request):
        logger.info(f"Booking request: {request.data}")
        serializer = BookingRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, status=400)

        try:
            with transaction.atomic():
                booking = serializer.save()
                payment = Payment.objects.create(
                    booking=booking, amount=booking.lsa.hourly_rate,
                    currency='INR', status='pending'
                )
                try:
                    requests.post(MOCK_PAYMENT_GATEWAY_URL,
                        json={"booking_id": booking.id, "amount": str(payment.amount)},
                        timeout=5)
                except requests.exceptions.RequestException as e:
                    logger.error(f"Gateway error: {e}")

                return Response({
                    "success": True,
                    "message": "Booking created successfully.",
                    "booking": BookingRequestSerializer(booking).data,
                    "payment_id": payment.id,
                    "payment_status": payment.status,
                }, status=201)

        except DjangoValidationError as e:
            return Response({"success": False, "errors": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error: {e}")
            return Response({"success": False, "error": str(e)}, status=500)


class LSASearchView(APIView):
    """GET /api/v1/lsas/search/ — Search available LSAs, N+1 optimised"""

    def get(self, request):
        skill = request.query_params.get('skill', None)
        queryset = LSAProfile.objects.filter(is_available=True).prefetch_related('bookings')
        if skill:
            # Python-level filter for SQLite compatibility (PostgreSQL uses __contains)
            all_lsas = list(queryset)
            queryset = [lsa for lsa in all_lsas if skill in lsa.skills]
            return Response({"success": True, "count": len(queryset),
                             "results": LSAProfileSerializer(queryset, many=True).data})
        serializer = LSAProfileSerializer(queryset, many=True)
        return Response({"success": True, "count": queryset.count(),
                         "results": serializer.data})


class PaymentWebhookView(APIView):
    """POST /api/payments/webhook/ — Handle payment events, transition booking state"""

    def post(self, request):
        payload = request.data
        for field in ['booking_id', 'payment_status', 'gateway_reference']:
            if field not in payload:
                return Response({"success": False, "error": f"Missing: {field}"}, status=400)

        try:
            payment = Payment.objects.select_related('booking').get(
                booking_id=payload['booking_id'])
        except Payment.DoesNotExist:
            return Response({"success": False, "error": "Payment not found."}, status=404)

        with transaction.atomic():
            payment.webhook_payload = payload
            payment.gateway_reference = payload.get('gateway_reference', '')
            ps = payload['payment_status']
            if ps == 'success':
                payment.status = 'success'
                payment.booking.status = 'confirmed'
            elif ps == 'failed':
                payment.status = 'failed'
                payment.booking.status = 'cancelled'
            else:
                return Response({"success": False, "error": "Invalid payment_status."}, status=400)
            payment.save()
            payment.booking.save()

        return Response({"success": True,
                         "message": f"Booking {payload['booking_id']} updated.",
                         "payment_status": payment.status,
                         "booking_status": payment.booking.status})
