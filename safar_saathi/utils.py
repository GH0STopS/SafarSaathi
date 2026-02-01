from django.contrib.auth.models import Group


def is_patient(user):
    """Check if user is a patient"""
    return user.groups.filter(name='Patient').exists() and hasattr(user, 'patientprofile')


def is_clinic_staff(user):
    """Check if user is clinic staff"""
    return user.groups.filter(name='Clinic').exists() and hasattr(user, 'clinicprofile')


def is_admin(user):
    """Check if user is an admin"""
    return user.is_staff or user.groups.filter(name='Admin').exists()