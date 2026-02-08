from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    current_location = models.CharField(max_length=100)  # City/State
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    current_clinic = models.ForeignKey(
        'clinic.ClinicProfile', on_delete=models.SET_NULL, null=True, blank=True)
    consent_given = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, help_text="Whether this patient profile is active")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.current_location}"


class TreatmentRecord(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    clinic = models.ForeignKey(
        'clinic.ClinicProfile', on_delete=models.CASCADE)
    disease = models.CharField(max_length=100, default='HIV')  
    record_date = models.DateTimeField(default=timezone.now)
    details = models.TextField()  # Append-only treatment details
    is_emergency = models.BooleanField(default=False)

    class Meta:
        ordering = ['-record_date']

    def __str__(self):
        return f"{self.patient.user.username} - {self.record_date}"


class TransferRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    from_clinic = models.ForeignKey(
        'clinic.ClinicProfile', related_name='transfer_from', on_delete=models.CASCADE)
    to_clinic = models.ForeignKey(
        'clinic.ClinicProfile', related_name='transfer_to', on_delete=models.CASCADE)
    request_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField()

    def __str__(self):
        return f"Transfer {self.patient.user.username} from {self.from_clinic.name} to {self.to_clinic.name}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    clinic = models.ForeignKey('clinic.ClinicProfile', on_delete=models.CASCADE)
    # doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_appointments')
    appointment_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    appointment_type = models.CharField(max_length=50, choices=[
        ('general', 'General Consultation'),
        ('follow_up', 'Follow-up'),
        ('emergency', 'Emergency'),
        ('checkup', 'Regular Checkup'),
    ], default='consultation')
    consultation_mode = models.CharField(max_length=20, choices=[
        ('in_person', 'In Person'),
        ('online', 'Online/Video Call'),
        ('phone', 'Phone Call'),
    ], default='in_person')
    meeting_link = models.URLField(blank=True, help_text="Video call link for online consultations")
    meeting_id = models.CharField(max_length=100, blank=True, help_text="Meeting ID for online consultations")
    meeting_password = models.CharField(max_length=50, blank=True, help_text="Meeting password if required")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    password_viewed = models.BooleanField(default=False, help_text="Whether the patient has viewed the appointment password")

    class Meta:
        ordering = ['-appointment_date']

    def __str__(self):
        return f"{self.patient.user.username} - {self.appointment_date}"


class CounsellingSession(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    clinic = models.ForeignKey('clinic.ClinicProfile', on_delete=models.CASCADE)
    counsellor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='counselling_sessions')
    session_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    session_type = models.CharField(max_length=50, choices=[
        ('individual', 'Individual Counselling'),
        ('group', 'Group Counselling'),
        ('family', 'Family Counselling'),
        ('crisis', 'Crisis Intervention'),
    ], default='individual')
    session_mode = models.CharField(max_length=20, choices=[
        ('in_person', 'In Person'),
        ('online', 'Online/Video Call'),
        ('phone', 'Phone Call'),
    ], default='in_person')
    meeting_link = models.URLField(blank=True, help_text="Video call link for online sessions")
    meeting_id = models.CharField(max_length=100, blank=True, help_text="Meeting ID for online sessions")
    meeting_password = models.CharField(max_length=50, blank=True, help_text="Meeting password if required")
    notes = models.TextField(blank=True)
    medical_updates = models.TextField(blank=True, help_text="Medical data updates from session")
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-session_date']

    def __str__(self):
        return f"Counselling: {self.patient.user.username} - {self.session_date}"


class ExternalConsultation(models.Model):
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    requesting_clinic = models.ForeignKey('clinic.ClinicProfile', on_delete=models.CASCADE, related_name='external_consultations_requested')
    parent_clinic = models.ForeignKey('clinic.ClinicProfile', on_delete=models.CASCADE, related_name='external_consultations_parent')
    consultation_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    consultation_type = models.CharField(max_length=50, choices=[
        ('specialist_consultation', 'Specialist Consultation'),
        ('emergency_care', 'Emergency Care'),
        ('follow_up', 'Follow-up Care'),
        ('diagnostic_services', 'Diagnostic Services'),
    ], default='specialist_consultation')
    reason = models.TextField(help_text="Reason for external consultation")
    current_location = models.CharField(max_length=100, help_text="Patient's current location")
    stay_type = models.CharField(max_length=20, choices=[
        ('temporary', 'Temporary Stay'),
        ('permanent', 'Permanent Stay'),
    ], default='temporary')
    medical_data_access_granted = models.BooleanField(default=False)
    access_expiry = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-consultation_date']

    def __str__(self):
        return f"External Consultation: {self.patient.user.username} - {self.requesting_clinic.name}"

    def grant_medical_access(self):
        """Grant medical data access based on stay type"""
        if self.stay_type == 'permanent':
            # Permanent stay - full access, no expiry
            self.medical_data_access_granted = True
            self.access_expiry = None
        else:
            # Temporary stay - one-time access, expires after consultation
            self.medical_data_access_granted = True
            self.access_expiry = self.consultation_date + timedelta(hours=24)
        self.save()


class MedicalDataRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('expired', 'Expired'),
    ]
    requesting_clinic = models.ForeignKey('clinic.ClinicProfile', on_delete=models.CASCADE, related_name='medical_data_requests')
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    parent_clinic = models.ForeignKey('clinic.ClinicProfile', on_delete=models.CASCADE, related_name='medical_data_requests_parent')
    request_reason = models.TextField()
    requested_data_types = models.JSONField(default=list, help_text="List of data types requested")
    access_duration = models.CharField(max_length=20, choices=[
        ('one_time', 'One-time Access'),
        ('temporary', 'Temporary Access'),
        ('permanent', 'Permanent Access'),
    ], default='one_time')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    access_granted_until = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Medical Data Request: {self.patient.user.username} - {self.requesting_clinic.name}"

    def approve_request(self, approved_by, access_duration_days=None):
        """Approve the medical data request"""
        self.status = 'approved'
        self.approved_by = approved_by
        self.approval_date = timezone.now()

        if self.access_duration == 'one_time':
            self.access_granted_until = timezone.now() + timedelta(hours=24)
        elif self.access_duration == 'temporary':
            days = access_duration_days or 30
            self.access_granted_until = timezone.now() + timedelta(days=days)
        else:  # permanent
            self.access_granted_until = None

        self.save()

    def deny_request(self, approved_by, reason=""):
        """Deny the medical data request"""
        self.status = 'denied'
        self.approved_by = approved_by
        self.approval_date = timezone.now()
        self.notes = reason
        self.save()


class Prescription(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    clinic = models.ForeignKey('clinic.ClinicProfile', on_delete=models.CASCADE)
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions')
    prescription_date = models.DateTimeField(default=timezone.now)
    diagnosis = models.TextField()
    medications = models.JSONField(default=list, help_text="List of medications with dosage")
    instructions = models.TextField(blank=True)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-prescription_date']

    def __str__(self):
        return f"Prescription: {self.patient.user.username} - {self.prescription_date}"


class MedicationReminder(models.Model):
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='medication_reminders'
    )

    medication_name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50)

    frequency = models.CharField(
        max_length=50,
        help_text="e.g. once daily, twice daily, every 8 hours"
    )

    

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    last_reminder_sent = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Reminder: {self.medication_name} for {self.prescription.patient.user.username}"
    
# class MedicationList(models.Model):
#     medication = models.ForeignKey(MedicationReminder, on_delete=models.CASCADE, related_name='medication_lists')
#     intake_time = models.TimeField()
#     has_taken = models.BooleanField(default=False)
#     created_at = models.DateTimeField(default=timezone.now)
    
#     class Meta:
#         ordering = ['-intake_time']
#         unique_together = ['medication', 'intake_time']
     
#     def __str__(self):
#         return f"{self.medication.medication_name} at {self.intake_time}"
    

# class MedicationLog(models.Model):
#     reminder = models.ForeignKey(MedicationReminder, on_delete=models.CASCADE)
#     scheduled_time = models.DateTimeField()
#     taken_time = models.DateTimeField(null=True, blank=True)
#     was_taken = models.BooleanField(default=False)
#     notes = models.TextField(blank=True)
#     created_at = models.DateTimeField(default=timezone.now)

#     class Meta:
#         ordering = ['-scheduled_time']
#         unique_together = ['reminder', 'scheduled_time']

#     def __str__(self):
#         status = "Taken" if self.was_taken else "Missed"
#         return f"{status}: {self.reminder.medication_name} at {self.scheduled_time}"

class MedicationIntake(models.Model):
    reminder = models.ForeignKey(
        MedicationReminder,
        on_delete=models.CASCADE,
        related_name='intakes'
    )

    intake_time = models.TimeField()
    intake_date = models.DateField(default=timezone.now)
    has_taken = models.BooleanField(default=False)
    taken_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['reminder', 'intake_date', 'intake_time']
        ordering = ['intake_time']

    def __str__(self):
        status = "Taken" if self.has_taken else "Pending"
        return f"{self.reminder.medication_name} at {self.intake_time} ({status})"



class TelemedicineSession(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='telemedicine_sessions')
    clinic = models.ForeignKey('clinic.ClinicProfile', on_delete=models.CASCADE)
    session_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    session_type = models.CharField(max_length=50, choices=[
        ('consultation', 'Video Consultation'),
        ('follow_up', 'Follow-up'),
        ('emergency', 'Emergency Consultation'),
    ], default='consultation')
    meeting_link = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    recording_url = models.URLField(blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-session_date']

    def __str__(self):
        return f"Telemedicine: {self.patient.user.username} - {self.session_date}"


class HealthMetric(models.Model):
    METRIC_TYPES = [
        ('weight', 'Weight (kg)'),
        ('blood_pressure_systolic', 'Blood Pressure Systolic'),
        ('blood_pressure_diastolic', 'Blood Pressure Diastolic'),
        ('heart_rate', 'Heart Rate (bpm)'),
        ('temperature', 'Temperature (°C)'),
        ('blood_sugar', 'Blood Sugar (mg/dL)'),
        ('oxygen_saturation', 'Oxygen Saturation (%)'),
        ('steps', 'Daily Steps'),
        ('sleep_hours', 'Sleep Hours'),
    ]
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES)
    value = models.FloatField()
    unit = models.CharField(max_length=20, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)
    source = models.CharField(max_length=50, choices=[
        ('manual', 'Manual Entry'),
        ('device', 'Wearable Device'),
        ('clinic', 'Clinic Measurement'),
    ], default='manual')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['patient', 'metric_type', 'recorded_at']),
        ]

    def __str__(self):
        return f"{self.metric_type}: {self.value} for {self.patient.user.username}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('appointment_reminder', 'Appointment Reminder'),
        ('medication_reminder', 'Medication Reminder'),
        ('emergency_alert', 'Emergency Alert'),
        ('transfer_request', 'Transfer Request'),
        ('general', 'General Notification'),
    ]

    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)  # For scheduled notifications

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', 'is_read', 'created_at']),
            models.Index(fields=['scheduled_at']),
        ]

    def __str__(self):
        return f"{self.notification_type}: {self.title} for {self.patient.user.username}"
