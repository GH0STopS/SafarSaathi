from django.urls import path
from . import views

app_name = 'mental_health'

urlpatterns = [
    path('dashboard/', views.mental_health_dashboard, name='mental_health_dashboard'),
    path('request/', views.request_session, name='request_session'),
]
