from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404
from .models import AuditLog
from clinic.models import ClinicProfile, Disease
from patient.models import PatientProfile
from emergency.models import EmergencyAccess
from django.contrib import messages
from django.utils import timezone
from safar_saathi.utils import is_admin
import logging

logger = logging.getLogger(__name__)


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    try:
        clinics = ClinicProfile.objects.all()
        audit_logs = AuditLog.objects.all()[:10]  # Last 10 logs
        total_users = PatientProfile.objects.count() + ClinicProfile.objects.count()
        total_emergencies = EmergencyAccess.objects.count()
        approved_clinics = ClinicProfile.objects.filter(is_approved=True).count()
        pending_clinics = ClinicProfile.objects.filter(is_approved=False).count()
        active_patients = PatientProfile.objects.filter(is_active=True).count()
        inactive_patients = PatientProfile.objects.filter(is_active=False).count()
        active_clinics = ClinicProfile.objects.filter(is_active=True).count()
        inactive_clinics = ClinicProfile.objects.filter(is_active=False).count()
        context = {
            'clinics': clinics,
            'audit_logs': audit_logs,
            'total_users': total_users,
            'total_emergencies': total_emergencies,
            'approved_clinics': approved_clinics,
            'pending_clinics': pending_clinics,
            'active_patients': active_patients,
            'inactive_patients': inactive_patients,
            'active_clinics': active_clinics,
            'inactive_clinics': inactive_clinics,
            'current_time': timezone.now(),
        }
        return render(request, 'admin_app/dashboard.html', context)
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {str(e)}", exc_info=True)
        messages.error(request, 'An error occurred while loading the dashboard.')
        return redirect('home')


@login_required
@user_passes_test(is_admin)
def approve_clinic(request, clinic_id):
    try:
        with transaction.atomic():
            clinic = get_object_or_404(ClinicProfile, id=clinic_id)

            if clinic.is_approved:
                messages.warning(request, f'Clinic {clinic.name} is already approved.')
                return redirect('admin_app:admin_dashboard')

            clinic.is_approved = True
            clinic.save()

            AuditLog.objects.create(
                user=request.user,
                action='approve',
                details=f'Approved clinic {clinic.name}'
            )

            logger.info(f"Clinic approved: {clinic.name} by {request.user.username}")
            messages.success(request, f'Clinic {clinic.name} approved successfully.')
            return redirect('admin_app:admin_dashboard')

    except IntegrityError as e:
        logger.error(f"Database integrity error approving clinic {clinic_id}: {str(e)}")
        messages.error(request, 'A database error occurred. Please try again.')
    except Exception as e:
        logger.error(f"Unexpected error approving clinic {clinic_id}: {str(e)}", exc_info=True)
        messages.error(request, 'An unexpected error occurred. Please try again.')

    return redirect('admin_app:admin_dashboard')


@login_required
@user_passes_test(is_admin)
def reject_clinic(request, clinic_id):
    try:
        with transaction.atomic():
            clinic = get_object_or_404(ClinicProfile, id=clinic_id)

            if clinic.is_approved:
                messages.warning(request, f'Cannot reject an already approved clinic. Please contact support.')
                return redirect('admin_app:admin_dashboard')

            clinic_name = clinic.name
            clinic.delete()

            AuditLog.objects.create(
                user=request.user,
                action='reject',
                details=f'Rejected clinic {clinic_name}'
            )

            logger.info(f"Clinic rejected: {clinic_name} by {request.user.username}")
            messages.success(request, f'Clinic {clinic_name} rejected successfully.')

    except IntegrityError as e:
        logger.error(f"Database integrity error rejecting clinic {clinic_id}: {str(e)}")
        messages.error(request, 'A database error occurred. Please try again.')
    except Exception as e:
        logger.error(f"Unexpected error rejecting clinic {clinic_id}: {str(e)}", exc_info=True)
        messages.error(request, 'An unexpected error occurred. Please try again.')

    return redirect('admin_app:admin_dashboard')
    return redirect('admin_app:admin_dashboard')


@login_required
@user_passes_test(is_admin)
def user_management(request):
    patients = PatientProfile.objects.all()
    clinics = ClinicProfile.objects.all()
    context = {
        'patients': patients,
        'clinics': clinics,
    }
    return render(request, 'admin_app/user_management.html', context)


@login_required
@user_passes_test(is_admin)
def audit_logs(request):
    logs = AuditLog.objects.all().order_by('-timestamp')
    
    # Filtering
    user_filter = request.GET.get('user')
    action_filter = request.GET.get('action')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if user_filter:
        logs = logs.filter(user__username__icontains=user_filter)
    if action_filter:
        logs = logs.filter(action=action_filter)
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)
    
    context = {
        'logs': logs,
        'user_filter': user_filter,
        'action_filter': action_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'admin_app/audit_logs.html', context)


@login_required
@user_passes_test(is_admin)
def edit_patient(request, patient_id):
    patient = get_object_or_404(PatientProfile, id=patient_id)
    if request.method == 'POST':
        patient.disease = request.POST.get('disease')
        clinic_id = request.POST.get('current_clinic')
        if clinic_id:
            patient.current_clinic = get_object_or_404(ClinicProfile, id=clinic_id)
        else:
            patient.current_clinic = None
        patient.save()
        AuditLog.objects.create(user=request.user, action='update', details=f'Updated patient {patient.user.username}')
        messages.success(request, f'Patient {patient.user.username} updated.')
        return redirect('admin_app:user_management')
    clinics = ClinicProfile.objects.filter(is_approved=True)
    context = {
        'patient': patient,
        'clinics': clinics,
    }
    return render(request, 'admin_app/edit_patient.html', context)


@login_required
@user_passes_test(is_admin)
def edit_clinic(request, clinic_id):
    clinic = get_object_or_404(ClinicProfile, id=clinic_id)
    if request.method == 'POST':
        clinic.name = request.POST.get('name')
        clinic.address = request.POST.get('address')
        clinic.diseases_treated = request.POST.get('diseases_treated')
        clinic.save()
        AuditLog.objects.create(user=request.user, action='update', details=f'Updated clinic {clinic.name}')
        messages.success(request, f'Clinic {clinic.name} updated.')
        return redirect('admin_app:user_management')
    context = {
        'clinic': clinic,
    }
    return render(request, 'admin_app/edit_clinic.html', context)


@login_required
@user_passes_test(is_admin)
def deactivate_patient(request, patient_id):
    try:
        with transaction.atomic():
            patient = get_object_or_404(PatientProfile, id=patient_id)

            if not patient.is_active:
                messages.warning(request, f'Patient {patient.user.username} is already deactivated.')
                return redirect('admin_app:user_management')

            patient.is_active = False
            patient.save()

            AuditLog.objects.create(
                user=request.user,
                action='deactivate',
                details=f'Deactivated patient {patient.user.username}'
            )

            logger.info(f"Patient deactivated: {patient.user.username} by {request.user.username}")
            messages.success(request, f'Patient {patient.user.username} deactivated successfully.')
            return redirect('admin_app:user_management')

    except IntegrityError as e:
        logger.error(f"Database integrity error deactivating patient {patient_id}: {str(e)}")
        messages.error(request, 'A database error occurred. Please try again.')
    except Exception as e:
        logger.error(f"Unexpected error deactivating patient {patient_id}: {str(e)}", exc_info=True)
        messages.error(request, 'An unexpected error occurred. Please try again.')

    return redirect('admin_app:user_management')


@login_required
@user_passes_test(is_admin)
def activate_patient(request, patient_id):
    try:
        with transaction.atomic():
            patient = get_object_or_404(PatientProfile, id=patient_id)

            if patient.is_active:
                messages.warning(request, f'Patient {patient.user.username} is already active.')
                return redirect('admin_app:user_management')

            patient.is_active = True
            patient.save()

            AuditLog.objects.create(
                user=request.user,
                action='activate',
                details=f'Activated patient {patient.user.username}'
            )

            logger.info(f"Patient activated: {patient.user.username} by {request.user.username}")
            messages.success(request, f'Patient {patient.user.username} activated successfully.')
            return redirect('admin_app:user_management')

    except IntegrityError as e:
        logger.error(f"Database integrity error activating patient {patient_id}: {str(e)}")
        messages.error(request, 'A database error occurred. Please try again.')
    except Exception as e:
        logger.error(f"Unexpected error activating patient {patient_id}: {str(e)}", exc_info=True)
        messages.error(request, 'An unexpected error occurred. Please try again.')

    return redirect('admin_app:user_management')


@login_required
@user_passes_test(is_admin)
def deactivate_clinic(request, clinic_id):
    try:
        with transaction.atomic():
            clinic = get_object_or_404(ClinicProfile, id=clinic_id)

            if not clinic.is_active:
                messages.warning(request, f'Clinic {clinic.name} is already deactivated.')
                return redirect('admin_app:user_management')

            clinic.is_active = False
            clinic.save()

            AuditLog.objects.create(
                user=request.user,
                action='deactivate',
                details=f'Deactivated clinic {clinic.name}'
            )

            logger.info(f"Clinic deactivated: {clinic.name} by {request.user.username}")
            messages.success(request, f'Clinic {clinic.name} deactivated successfully.')
            return redirect('admin_app:user_management')

    except IntegrityError as e:
        logger.error(f"Database integrity error deactivating clinic {clinic_id}: {str(e)}")
        messages.error(request, 'A database error occurred. Please try again.')
    except Exception as e:
        logger.error(f"Unexpected error deactivating clinic {clinic_id}: {str(e)}", exc_info=True)
        messages.error(request, 'An unexpected error occurred. Please try again.')

    return redirect('admin_app:user_management')


@login_required
@user_passes_test(is_admin)
def activate_clinic(request, clinic_id):
    try:
        with transaction.atomic():
            clinic = get_object_or_404(ClinicProfile, id=clinic_id)

            if clinic.is_active:
                messages.warning(request, f'Clinic {clinic.name} is already active.')
                return redirect('admin_app:user_management')

            clinic.is_active = True
            clinic.save()

            AuditLog.objects.create(
                user=request.user,
                action='activate',
                details=f'Activated clinic {clinic.name}'
            )

            logger.info(f"Clinic activated: {clinic.name} by {request.user.username}")
            messages.success(request, f'Clinic {clinic.name} activated successfully.')
            return redirect('admin_app:user_management')

    except IntegrityError as e:
        logger.error(f"Database integrity error activating clinic {clinic_id}: {str(e)}")
        messages.error(request, 'A database error occurred. Please try again.')
        logger.error(f"Unexpected error activating clinic {clinic_id}: {str(e)}", exc_info=True)
        messages.error(request, 'An unexpected error occurred. Please try again.')

    return redirect('admin_app:user_management')


@login_required
@user_passes_test(is_admin)
def disease_management(request):
    diseases = Disease.objects.all().order_by('name')
    context = {
        'diseases': diseases,
    }
    return render(request, 'admin_app/disease_management.html', context)


@login_required
@user_passes_test(is_admin)
def add_disease(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not name:
            messages.error(request, 'Disease name is required.')
            return redirect('admin_app:disease_management')
        
        try:
            with transaction.atomic():
                disease = Disease.objects.create(
                    name=name,
                    description=description
                )
                
                AuditLog.objects.create(
                    user=request.user,
                    action='create',
                    details=f'Added new disease: {disease.name}'
                )
                
                logger.info(f"Disease added: {disease.name} by {request.user.username}")
                messages.success(request, f'Disease "{disease.name}" added successfully.')
                return redirect('admin_app:disease_management')
                
        except IntegrityError:
            messages.error(request, 'A disease with this name already exists.')
        except Exception as e:
            logger.error(f"Error adding disease: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred while adding the disease.')
    
    return redirect('admin_app:disease_management')


@login_required
@user_passes_test(is_admin)
def edit_disease(request, disease_id):
    disease = get_object_or_404(Disease, id=disease_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not name:
            messages.error(request, 'Disease name is required.')
            return redirect('admin_app:disease_management')
        
        try:
            with transaction.atomic():
                old_name = disease.name
                disease.name = name
                disease.description = description
                disease.save()
                
                AuditLog.objects.create(
                    user=request.user,
                    action='update',
                    details=f'Updated disease: {old_name} -> {disease.name}'
                )
                
                logger.info(f"Disease updated: {old_name} -> {disease.name} by {request.user.username}")
                messages.success(request, f'Disease "{disease.name}" updated successfully.')
                return redirect('admin_app:disease_management')
                
        except IntegrityError:
            messages.error(request, 'A disease with this name already exists.')
        except Exception as e:
            logger.error(f"Error updating disease: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred while updating the disease.')
    
    return redirect('admin_app:disease_management')


@login_required
@user_passes_test(is_admin)
def delete_disease(request, disease_id):
    disease = get_object_or_404(Disease, id=disease_id)
    
    # Check if disease is in use
    clinics_using = ClinicProfile.objects.filter(diseases_treated=disease).count()
    if clinics_using > 0:
        messages.error(request, f'Cannot delete disease "{disease.name}" as it is currently used by {clinics_using} clinic(s).')
        return redirect('admin_app:disease_management')
    
    try:
        with transaction.atomic():
            disease_name = disease.name
            disease.delete()
            
            AuditLog.objects.create(
                user=request.user,
                action='delete',
                details=f'Deleted disease: {disease_name}'
            )
            
            logger.info(f"Disease deleted: {disease_name} by {request.user.username}")
            messages.success(request, f'Disease "{disease_name}" deleted successfully.')
            
    except Exception as e:
        logger.error(f"Error deleting disease: {str(e)}", exc_info=True)
        messages.error(request, 'An error occurred while deleting the disease.')
    
    return redirect('admin_app:disease_management')

@login_required
@user_passes_test(is_admin)
def admin_profile(request):
    if request.method == 'POST':
        # Update user fields
        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name = request.POST.get('last_name', '').strip()
        request.user.email = request.POST.get('email', '').strip()
        request.user.save()

        messages.success(request, 'Profile updated successfully.')
        return redirect('admin_app:profile')

    context = {
        'user': request.user,
    }
    return render(request, 'admin_app/profile.html', context)