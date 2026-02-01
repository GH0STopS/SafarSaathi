from django.shortcuts import render, redirect
from django.http import Http404
from django.template import TemplateDoesNotExist
import logging

logger = logging.getLogger(__name__)


def home(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'patientprofile'):
            return redirect('patient:dashboard')
        elif hasattr(request.user, 'clinicprofile'):
            return redirect('clinic:clinic_dashboard')
        elif request.user.is_superuser:
            return redirect('admin_app:admin_dashboard')
        else:
            return redirect('home')
    return render(request, 'home.html')


def custom_404_view(request, exception):
    """Custom 404 error handler"""
    logger.warning(f"404 error: {request.path} - User: {request.user}")
    return render(request, 'errors/404.html', {
        'error_message': 'The page you are looking for does not exist.',
        'path': request.path
    }, status=404)


def custom_500_view(request):
    """Custom 500 error handler"""
    logger.error(f"500 error: {request.path} - User: {request.user}", exc_info=True)
    return render(request, 'errors/500.html', {
        'error_message': 'An internal server error occurred. Please try again later.',
    }, status=500)


def custom_403_view(request, exception):
    """Custom 403 error handler"""
    logger.warning(f"403 error: {request.path} - User: {request.user} - Reason: {exception}")
    return render(request, 'errors/403.html', {
        'error_message': 'You do not have permission to access this page.',
    }, status=403)


def custom_400_view(request, exception):
    """Custom 400 error handler"""
    logger.warning(f"400 error: {request.path} - User: {request.user} - Reason: {exception}")
    return render(request, 'errors/400.html', {
        'error_message': 'Bad request. Please check your input and try again.',
    }, status=400)
