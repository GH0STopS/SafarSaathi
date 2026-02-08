from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class EmergencyAccess(models.Model):
    patient = models.ForeignKey(
        'patient.PatientProfile', on_delete=models.CASCADE)
    clinic = models.ForeignKey(
        'clinic.ClinicProfile', on_delete=models.CASCADE)
    requested_by = models.ForeignKey(
        User, on_delete=models.CASCADE)  # Patient or Clinic staff
    request_time = models.DateTimeField(default=timezone.now)
    expiry_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    reason = models.TextField()
    emergency_type = models.CharField(max_length=50, choices=[
        ('medical', 'Medical Emergency'),
        ('violence', 'Violence/Domestic Abuse'),
        ('overdose', 'Drug Overdose'),
        ('suicide', 'Suicidal Thoughts'),
        ('other', 'Other'),
    ], default='medical')
    severity_level = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='medium')
    location_lat = models.FloatField(null=True, blank=True)
    location_lng = models.FloatField(null=True, blank=True)
    location_address = models.TextField(blank=True)
    emergency_contacts_notified = models.BooleanField(default=False)
    response_time = models.DurationField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.expiry_time:
            self.expiry_time = self.request_time + \
                timedelta(hours=24)  # Default 24 hours
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expiry_time

    def __str__(self):
        return f"Emergency Access for {self.patient.user.username} at {self.clinic.name}"


class EmergencyAlert(models.Model):
    ALERT_TYPES = [
        ('patient_triggered', 'Patient Triggered'),
        ('clinic_detected', 'Clinic Detected'),
        ('system_auto', 'System Auto-Alert'),
    ]
    patient = models.ForeignKey('patient.PatientProfile', on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    triggered_at = models.DateTimeField(default=timezone.now)
    location_lat = models.FloatField(null=True, blank=True)
    location_lng = models.FloatField(null=True, blank=True)
    location_address = models.TextField(blank=True)
    alert_message = models.TextField()
    is_active = models.BooleanField(default=True)
    responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='emergency_responses')
    response_time = models.DateTimeField(null=True, blank=True)
    resolution_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('responding', 'Responding'),
        ('resolved', 'Resolved'),
        ('false_alarm', 'False Alarm'),
    ], default='pending')
    resolution_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-triggered_at']

    def __str__(self):
        return f"Emergency Alert: {self.patient.user.username} - {self.alert_type}"


class EmergencyEvent(models.Model):
    access = models.OneToOneField(EmergencyAccess, on_delete=models.CASCADE)
    event_details = models.TextField()
    logged_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Emergency Event - {self.access.patient.user.username}"
