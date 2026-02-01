from django.contrib import admin
from patient.models import PatientProfile, TreatmentRecord, TransferRequest
from clinic.models import ClinicProfile
from admin_app.models import AuditLog
from emergency.models import EmergencyAccess, EmergencyEvent

# Register your models here.

admin.site.register(PatientProfile)
admin.site.register(TreatmentRecord)
admin.site.register(TransferRequest)
admin.site.register(ClinicProfile)
admin.site.register(AuditLog)
admin.site.register(EmergencyAccess)
admin.site.register(EmergencyEvent)
