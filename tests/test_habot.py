import json
from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from bookings.models import Parent, LSAProfile, BookingRequest, Payment


class TestLSASearch(TestCase):
    def setUp(self):
        self.client = Client()
        LSAProfile.objects.create(full_name="Priya Sharma", email="priya@test.com", skills=["dyslexia"], hourly_rate=500, is_available=True)
        LSAProfile.objects.create(full_name="Rahul Verma", email="rahul@test.com", skills=["adhd"], hourly_rate=600, is_available=False)

    def test_lsa_search_returns_only_available(self):
        response = self.client.get('/api/v1/lsas/search/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)

    def test_lsa_search_by_skill_filter(self):
        response = self.client.get('/api/v1/lsas/search/?skill=dyslexia')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)


class TestBookingCreate(TestCase):
    def setUp(self):
        self.client = Client()
        self.parent = Parent.objects.create(full_name="Ganesh Kumar", email="ganesh@test.com", phone="9999999999")
        self.lsa = LSAProfile.objects.create(full_name="Anitha Reddy", email="anitha@test.com", skills=["autism"], hourly_rate=700, is_available=True)
        self.now = timezone.now() + timedelta(hours=1)

    def test_booking_creation_success(self):
        payload = {"parent": self.parent.id, "lsa": self.lsa.id, "session_start": self.now.isoformat(), "session_end": (self.now + timedelta(hours=1)).isoformat()}
        response = self.client.post('/api/v1/bookings/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['success'])

    def test_booking_invalid_time_rejected(self):
        payload = {"parent": self.parent.id, "lsa": self.lsa.id, "session_start": (self.now + timedelta(hours=2)).isoformat(), "session_end": self.now.isoformat()}
        response = self.client.post('/api/v1/bookings/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)


class TestDoubleBookingPrevention(TestCase):
    def setUp(self):
        self.client = Client()
        self.parent = Parent.objects.create(full_name="Test Parent", email="parent@test.com", phone="8888888888")
        self.lsa = LSAProfile.objects.create(full_name="Test LSA", email="lsa@test.com", skills=["math"], hourly_rate=500, is_available=True)
        self.now = timezone.now() + timedelta(hours=1)
        BookingRequest.objects.create(parent=self.parent, lsa=self.lsa, session_start=self.now, session_end=self.now + timedelta(hours=1), status='confirmed')

    def test_overlapping_booking_rejected(self):
        payload = {"parent": self.parent.id, "lsa": self.lsa.id, "session_start": (self.now + timedelta(minutes=30)).isoformat(), "session_end": (self.now + timedelta(hours=2)).isoformat()}
        response = self.client.post('/api/v1/bookings/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)


class TestPaymentWebhook(TestCase):
    def setUp(self):
        self.client = Client()
        parent = Parent.objects.create(full_name="Webhook Parent", email="webhook@test.com", phone="7777777777")
        lsa = LSAProfile.objects.create(full_name="Webhook LSA", email="wlsa@test.com", skills=["speech"], hourly_rate=800, is_available=True)
        now = timezone.now() + timedelta(hours=2)
        self.booking = BookingRequest.objects.create(parent=parent, lsa=lsa, session_start=now, session_end=now + timedelta(hours=1), status='pending')
        self.payment = Payment.objects.create(booking=self.booking, amount=800, currency='INR', status='pending')

    def test_webhook_success_confirms_booking(self):
        payload = {"booking_id": self.booking.id, "payment_status": "success", "gateway_reference": "TXN_001"}
        response = self.client.post('/api/payments/webhook/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['booking_status'], 'confirmed')

    def test_webhook_failure_cancels_booking(self):
        payload = {"booking_id": self.booking.id, "payment_status": "failed", "gateway_reference": "TXN_FAIL"}
        response = self.client.post('/api/payments/webhook/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['booking_status'], 'cancelled')


class TestValidations(TestCase):
    def setUp(self):
        self.client = Client()

    def test_booking_missing_fields(self):
        response = self.client.post('/api/v1/bookings/', data=json.dumps({"notes": "test"}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])

    def test_webhook_missing_fields(self):
        response = self.client.post('/api/payments/webhook/', data=json.dumps({"booking_id": 999}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
