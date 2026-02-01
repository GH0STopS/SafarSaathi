from django.urls import path
from . import views

app_name = 'emergency'

urlpatterns = [
    path('dashboard/', views.emergency_dashboard, name='emergency_dashboard'),
    path('trigger/', views.trigger_emergency, name='trigger_emergency'),
    path('alerts/', views.emergency_alerts, name='emergency_alerts'),
    path('respond/<int:alert_id>/', views.respond_to_emergency, name='respond_to_emergency'),
]
