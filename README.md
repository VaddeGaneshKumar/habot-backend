# HabotConnect — LSA Booking Backend API
**Developer:** Vadde Ganesh Kumar | vaddeganeshkumar.data@gmail.com
**GitHub:** github.com/VaddeGaneshKumar

---

## Project Overview
Production-ready Django REST API backend for HabotConnect's LSA (Learning Support Assistant) booking platform. Built with Django MVT architecture, DRF, and automated Poka-Yoke validation.

---

## Architecture: Django MVT
- **Models** — Parent, LSAProfile, BookingRequest, Payment (normalized, indexed)
- **Views** — APIView classes with business logic
- **Templates** — Not used (pure API backend)
- **Serializers** — Input validation + overlap detection

---

## Database Schema

### Parent
| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | PK |
| full_name | CharField(200) | |
| email | EmailField | Unique, Indexed |
| phone | CharField(20) | |

### LSAProfile
| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | PK |
| full_name | CharField(200) | |
| email | EmailField | Unique, Indexed |
| skills | JSONField | List of skill keys |
| hourly_rate | DecimalField | |
| is_available | BooleanField | Indexed |

### BookingRequest
| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | PK |
| parent | FK → Parent | Indexed |
| lsa | FK → LSAProfile | Indexed |
| session_start | DateTimeField | Indexed |
| session_end | DateTimeField | |
| status | CharField | pending/confirmed/cancelled/completed |

### Payment
| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | PK |
| booking | OneToOne → BookingRequest | |
| amount | DecimalField | |
| status | CharField | pending/success/failed/refunded |
| gateway_reference | CharField | |
| webhook_payload | JSONField | Raw webhook data |

---

## API Endpoints

### POST /api/v1/bookings/
Create a new booking with Poka-Yoke double-booking prevention.

**Request:**
```json
{
  "parent": 1,
  "lsa": 2,
  "session_start": "2026-08-10T10:00:00Z",
  "session_end": "2026-08-10T11:00:00Z",
  "notes": "Child needs dyslexia support"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Booking created successfully.",
  "booking": { "id": 1, "status": "pending", ... },
  "payment_id": 1,
  "payment_status": "pending"
}
```

**Error (400) — Overlap:**
```json
{
  "success": false,
  "errors": "This LSA already has a booking overlapping this time slot."
}
```

---

### GET /api/v1/lsas/search/?skill=dyslexia
Search available LSAs. N+1 problem solved using prefetch_related.

**Response (200):**
```json
{
  "success": true,
  "count": 2,
  "results": [{ "id": 1, "full_name": "Priya Sharma", "skills": ["dyslexia"], ... }]
}
```

---

### POST /api/payments/webhook/
Handles payment gateway events — dynamically transitions booking state.

**Request:**
```json
{
  "booking_id": 1,
  "payment_status": "success",
  "gateway_reference": "TXN_001"
}
```

**Response (200):**
```json
{
  "success": true,
  "booking_status": "confirmed",
  "payment_status": "success"
}
```

---

## Query Optimization — N+1 Fix
```python
# BAD (N+1): Each LSA triggers separate booking query
lsas = LSAProfile.objects.filter(is_available=True)
for lsa in lsas:
    bookings = lsa.bookings.all()  # N extra queries!

# GOOD (Fixed): Single query with prefetch
lsas = LSAProfile.objects.filter(is_available=True).prefetch_related('bookings')
```

---

## Setup Instructions

```bash
# 1. Clone repo
git clone https://github.com/VaddeGaneshKumar/habot-backend.git
cd habot-backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Run server
python manage.py runserver

# 5. Run tests
python manage.py test tests --verbosity=2
```

---

## Test Coverage (9 Test Cases)
| Test | Description |
|------|-------------|
| test_lsa_search_returns_only_available | Only available LSAs returned |
| test_lsa_search_by_skill_filter | Skill filter works correctly |
| test_booking_creation_success | Valid booking created |
| test_booking_invalid_time_rejected | End before start rejected |
| test_overlapping_booking_rejected | Double-booking prevented |
| test_webhook_success_confirms_booking | Payment success → confirmed |
| test_webhook_failure_cancels_booking | Payment failure → cancelled |
| test_booking_missing_fields | Missing fields rejected |
| test_webhook_missing_fields | Incomplete webhook rejected |

---

## CI/CD Pipeline
GitHub Actions workflow runs on every push/PR:
- Python 3.12 setup
- Dependency install
- All 9 tests executed
- Migration check
