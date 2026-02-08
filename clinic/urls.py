from django.urls import path
from . import views

app_name = 'clinic'

urlpatterns = [
    path('register/', views.clinic_register, name='clinic_register'),
    path('dashboard/', views.clinic_dashboard, name='clinic_dashboard'),
    path('profile/', views.clinic_profile, name='profile'),
    path('transfer_request/', views.clinic_transfer_request,
         name='clinic_transfer_request'),
    path('approve_transfer/<int:request_id>/',
         views.approve_transfer, name='approve_transfer'),
    path('reject_transfer/<int:request_id>/',
         views.reject_transfer, name='reject_transfer'),
    path('add_treatment/', views.add_treatment_record,
         name='add_treatment_record'),
    path('manage_appointments/', views.manage_appointments, name='manage_appointments'),
    path('update_appointment/<int:appointment_id>/', views.update_appointment_status, name='update_appointment'),
    path('manage_counselling/', views.manage_counselling_sessions, name='manage_counselling_sessions'),
    path('schedule_counselling/', views.schedule_counselling_session, name='schedule_counselling'),
    path('update_counselling/<int:session_id>/', views.update_counselling_session, name='update_counselling_session'),
    path('external_consultations/', views.external_consultations, name='external_consultations'),
    path('approve_external/<int:consultation_id>/', views.approve_external_consultation, name='approve_external_consultation'),
    path('medical_data_requests/', views.medical_data_requests, name='medical_data_requests'),
    path('approve_data_request/<int:request_id>/', views.approve_medical_data_request, name='approve_data_request'),
    path('deny_data_request/<int:request_id>/', views.deny_medical_data_request, name='deny_data_request'),
    path('manage_prescriptions/', views.manage_prescriptions, name='manage_prescriptions'),
#     path('create_prescription/', views.create_prescription, name='create_prescription'),
    path('update_prescription/<int:prescription_id>/', views.update_prescription, name='update_prescription'),
    path('telemedicine/', views.telemedicine_management, name='telemedicine_management'),
    path('update_telemedicine/<int:session_id>/', views.update_telemedicine_session, name='update_telemedicine_session'),
]
