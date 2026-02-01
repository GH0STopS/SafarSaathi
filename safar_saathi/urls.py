"""
URL configuration for safar_saathi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

# Error handlers
handler404 = views.custom_404_view
handler500 = views.custom_500_view
handler403 = views.custom_403_view
handler400 = views.custom_400_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('patient/', include('patient.urls', namespace='patient')),
    path('clinic/', include('clinic.urls', namespace='clinic')),
    path('admin_app/', include('admin_app.urls', namespace='admin_app')),
    path('emergency/', include('emergency.urls', namespace='emergency')),
    path('mental_health/', include('mental_health.urls', namespace='mental_health')),
]
