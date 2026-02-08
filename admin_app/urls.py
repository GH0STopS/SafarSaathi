from django.urls import path
from . import views

app_name = 'admin_app'

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('clinic_management/', views.clinic_management, name='clinic_management'),
    path('patient_management/', views.patient_management, name='patient_management'),
    path('approve_clinic/<int:clinic_id>/', views.approve_clinic, name='approve_clinic'),
    path('reject_clinic/<int:clinic_id>/', views.reject_clinic, name='reject_clinic'),
    path('audit_logs/', views.audit_logs, name='audit_logs'),
    path('edit_patient/<int:patient_id>/', views.edit_patient, name='edit_patient'),
    path('edit_clinic/<int:clinic_id>/', views.edit_clinic, name='edit_clinic'),
    path('deactivate_patient/<int:patient_id>/', views.deactivate_patient, name='deactivate_patient'),
    path('activate_patient/<int:patient_id>/', views.activate_patient, name='activate_patient'),
    path('deactivate_clinic/<int:clinic_id>/', views.deactivate_clinic, name='deactivate_clinic'),
    path('activate_clinic/<int:clinic_id>/', views.activate_clinic, name='activate_clinic'),
    path('disease_management/', views.disease_management, name='disease_management'),
    path('add_disease/', views.add_disease, name='add_disease'),
    path('edit_disease/<int:disease_id>/', views.edit_disease, name='edit_disease'),
    path('delete_disease/<int:disease_id>/', views.delete_disease, name='delete_disease'),
    path('profile/', views.admin_profile, name='profile'),
]
