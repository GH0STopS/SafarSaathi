from django.urls import path
from . import views

app_name = 'patient'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('transfer_request/', views.transfer_request, name='transfer_request'),
    path('nearby_clinics/', views.nearby_clinics, name='nearby_clinics'),
    path('clinic/<int:clinic_id>/', views.clinic_detail, name='clinic_detail'),
    path('emergency_trigger/', views.emergency_trigger, name='emergency_trigger'),
    path('book_appointment/', views.book_appointment, name='book_appointment'),
    path('my_appointments/', views.my_appointments, name='my_appointments'),
    path('my_counselling_sessions/', views.my_counselling_sessions, name='my_counselling_sessions'),
    path('external_consultations/', views.external_consultations, name='external_consultations'),
    path('book_external_consultation/', views.book_external_consultation, name='book_external_consultation'),
    path('my_prescriptions/', views.my_prescriptions, name='my_prescriptions'),
    path('telemedicine_sessions/', views.telemedicine_sessions, name='telemedicine_sessions'),
    path('book_telemedicine/', views.book_telemedicine_session, name='book_telemedicine'),
    path('health_metrics/', views.health_metrics, name='health_metrics'),
    path('add_health_metric/', views.add_health_metric, name='add_health_metric'),
]
