from django.db import models
from django.core.exceptions import ValidationError


class Parent(models.Model):
    """Parent entity - person booking LSA for their child"""
    full_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'parents'
        indexes = [models.Index(fields=['email'])]

    def __str__(self):
        return f"{self.full_name} ({self.email})"


class LSAProfile(models.Model):
    """Learning Support Assistant profile"""
    SKILL_CHOICES = [
        ('dyslexia', 'Dyslexia Support'),
        ('autism', 'Autism Support'),
        ('adhd', 'ADHD Support'),
        ('speech', 'Speech Therapy'),
        ('math', 'Math Learning Support'),
        ('reading', 'Reading Support'),
    ]

    full_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True, db_index=True)
    skills = models.JSONField(default=list)  # List of skill keys
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2)
    is_available = models.BooleanField(default=True, db_index=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lsa_profiles'
        indexes = [
            models.Index(fields=['is_available']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.full_name} - {self.skills}"


class BookingRequest(models.Model):
    """Booking Request entity - parent books an LSA for a session"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    parent = models.ForeignKey(
        Parent, on_delete=models.CASCADE,
        related_name='bookings', db_index=True
    )
    lsa = models.ForeignKey(
        LSAProfile, on_delete=models.CASCADE,
        related_name='bookings', db_index=True
    )
    session_start = models.DateTimeField(db_index=True)
    session_end = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='pending', db_index=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'booking_requests'
        indexes = [
            models.Index(fields=['lsa', 'session_start', 'session_end']),
            models.Index(fields=['status']),
        ]

    def clean(self):
        """Prevent overlapping bookings for same LSA - Poka-Yoke validation"""
        if self.session_start >= self.session_end:
            raise ValidationError("Session end must be after session start.")

        overlapping = BookingRequest.objects.filter(
            lsa=self.lsa,
            status__in=['pending', 'confirmed'],
            session_start__lt=self.session_end,
            session_end__gt=self.session_start,
        ).exclude(pk=self.pk)

        if overlapping.exists():
            raise ValidationError(
                f"LSA already has a booking overlapping this time slot."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.pk} | {self.parent} → {self.lsa} | {self.status}"


class Payment(models.Model):
    """Payment entity linked to a booking"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    booking = models.OneToOneField(
        BookingRequest, on_delete=models.CASCADE,
        related_name='payment', db_index=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='pending', db_index=True
    )
    gateway_reference = models.CharField(max_length=200, blank=True)
    webhook_payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        indexes = [models.Index(fields=['status'])]

    def __str__(self):
        return f"Payment {self.pk} | Booking {self.booking_id} | {self.status}"
