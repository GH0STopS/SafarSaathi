from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404
from .models import EmergencyAccess, EmergencyAlert
from patient.models import PatientProfile, MedicalDataRequest
from clinic.models import ClinicProfile
from safar_saathi.utils import is_patient, is_clinic_staff
import logging

logger = logging.getLogger(__name__)


@login_required
@user_passes_test(is_patient)
def emergency_dashboard(request):
    try:
        accesses = EmergencyAccess.objects.filter(patient__user=request.user)
        alerts = EmergencyAlert.objects.filter(patient__user=request.user).order_by('-triggered_at')[:5]
        context = {
            'accesses': accesses,
            'alerts': alerts,
        }
        return render(request, 'emergency/dashboard.html', context)
    except Exception as e:
        logger.error(f"Error loading emergency dashboard for user {request.user.username}: {str(e)}", exc_info=True)
        messages.error(request, 'An error occurred while loading your emergency dashboard.')
        return redirect('patient:dashboard')


@login_required
@user_passes_test(is_patient)
def trigger_emergency(request):
    try:
        patient = request.user.patientprofile
    except PatientProfile.DoesNotExist:
        logger.error(f"Patient profile not found for user: {request.user.username}")
        messages.error(request, 'Your patient profile is missing. Please contact support.')
        return redirect('home')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                emergency_type = request.POST.get('emergency_type', '').strip()
                severity_level = request.POST.get('severity_level', '').strip()
                location_lat = request.POST.get('location_lat', '').strip()
                location_lng = request.POST.get('location_lng', '').strip()
                location_address = request.POST.get('location_address', '').strip()
                alert_message = request.POST.get('alert_message', '').strip()

                # Validation
                if not emergency_type:
                    messages.error(request, 'Please select an emergency type.')
                    return redirect('emergency:trigger_emergency')

                if not severity_level:
                    messages.error(request, 'Please select a severity level.')
                    return redirect('emergency:trigger_emergency')

                if not alert_message:
                    messages.error(request, 'Please provide details about the emergency.')
                    return redirect('emergency:trigger_emergency')

                if len(alert_message) < 10:
                    messages.error(request, 'Please provide more detailed information about the emergency (at least 10 characters).')
                    return redirect('emergency:trigger_emergency')

                # Validate coordinates if provided
                if location_lat and location_lng:
                    try:
                        lat = float(location_lat)
                        lng = float(location_lng)
                        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                            messages.error(request, 'Invalid location coordinates.')
                            return redirect('emergency:trigger_emergency')
                    except ValueError:
                        messages.error(request, 'Invalid location coordinates format.')
                        return redirect('emergency:trigger_emergency')

                # Create emergency alert
                alert = EmergencyAlert.objects.create(
                    patient=patient,
                    alert_type='patient_triggered',
                    location_lat=location_lat or None,
                    location_lng=location_lng or None,
                    location_address=location_address,
                    alert_message=alert_message
                )

                # If patient has current clinic, create emergency access
                if patient.current_clinic:
                    EmergencyAccess.objects.create(
                        patient=patient,
                        clinic=patient.current_clinic,
                        requested_by=request.user,
                        reason=alert_message,
                        emergency_type=emergency_type,
                        severity_level=severity_level,
                        location_lat=location_lat or None,
                        location_lng=location_lng or None,
                        location_address=location_address
                    )

                logger.warning(f"Emergency alert triggered by patient {request.user.username}: {alert_message}")
                messages.success(request, 'Emergency alert sent! Help is on the way.')
                return redirect('emergency:emergency_dashboard')

        except IntegrityError as e:
            logger.error(f"Database integrity error in emergency trigger: {str(e)}")
            messages.error(request, 'A database error occurred. Please try again.')
        except Exception as e:
            logger.error(f"Unexpected error in emergency trigger: {str(e)}", exc_info=True)
            messages.error(request, 'An unexpected error occurred. Please try again.')

    try:
        context = {
            'patient': patient,
        }
        return render(request, 'emergency/trigger_emergency.html', context)
    except Exception as e:
        logger.error(f"Error loading emergency trigger form: {str(e)}", exc_info=True)
        messages.error(request, 'Error loading the emergency form.')
        return redirect('patient:dashboard')


@login_required
@user_passes_test(is_clinic_staff)
def emergency_alerts(request):
    clinic = request.user.clinicprofile

    # Get alerts for patients registered at this clinic
    registered_alerts = EmergencyAlert.objects.filter(
        patient__current_clinic=clinic,
        is_active=True
    )

    # Get nearby emergency alerts (patients not registered here but in emergency)
    # For now, we'll show all active alerts - in production, you'd filter by distance
    nearby_alerts = EmergencyAlert.objects.filter(
        is_active=True
    ).exclude(patient__current_clinic=clinic)

    # Combine and order by triggered time
    all_alerts = (registered_alerts | nearby_alerts).order_by('-triggered_at')

    context = {
        'alerts': all_alerts,
        'clinic': clinic,
        'registered_alerts_count': registered_alerts.count(),
        'nearby_alerts_count': nearby_alerts.count(),
    }
    return render(request, 'emergency/alerts.html', context)


@login_required
@user_passes_test(is_clinic_staff)
def respond_to_emergency(request, alert_id):
    alert = get_object_or_404(EmergencyAlert, id=alert_id)
    clinic = request.user.clinicprofile

    # Allow response to any active emergency alert (nearby clinics can respond)
    # No access restriction for emergency response - any clinic can help

    if request.method == 'POST':
        resolution_status = request.POST['resolution_status']
        resolution_notes = request.POST.get('resolution_notes', '')

        alert.responded_by = request.user
        alert.response_time = timezone.now()
        alert.resolution_status = resolution_status
        alert.resolution_notes = resolution_notes
        if resolution_status in ['resolved', 'false_alarm']:
            alert.is_active = False
        alert.save()

        # Auto-create medical data request for out-of-town patients
        if alert.patient.current_clinic != clinic:
            # Check if a similar request already exists and is active
            existing_request = MedicalDataRequest.objects.filter(
                requesting_clinic=clinic,
                patient=alert.patient,
                parent_clinic=alert.patient.current_clinic,
                status__in=['pending', 'approved'],
                created_at__date=timezone.now().date()  # Same day
            ).first()

            if not existing_request:
                # Create automatic medical data request
                medical_request = MedicalDataRequest.objects.create(
                    requesting_clinic=clinic,
                    patient=alert.patient,
                    parent_clinic=alert.patient.current_clinic,
                    request_reason=f"EMERGENCY RESPONSE: {alert.alert_message}. Critical medical data access required for emergency care.",
                    requested_data_types=[
                        "treatment_history",
                        "medications",
                        "allergies",
                        "emergency_contacts",
                        "chronic_conditions",
                        "recent_lab_results",
                        "vital_signs"
                    ],
                    access_duration='temporary',  # Emergency access
                    notes=f"Auto-generated during emergency response. Alert ID: {alert.id}"
                )
                messages.info(request, f'Critical medical data request automatically sent to {alert.patient.current_clinic.name}')

        messages.success(request, f'Emergency response recorded: {resolution_status}')
        return redirect('emergency:emergency_alerts')

    context = {
        'alert': alert,
        'is_nearby_response': alert.patient.current_clinic != clinic,
    }
    return render(request, 'emergency/respond_emergency.html', context)
