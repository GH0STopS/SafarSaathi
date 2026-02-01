from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404
from .models import PatientProfile, TransferRequest, TreatmentRecord, Appointment, CounsellingSession, ExternalConsultation, MedicalDataRequest, Prescription, MedicationReminder, TelemedicineSession, HealthMetric
from .forms import PatientRegistrationForm, TransferRequestForm, AppointmentBookingForm
from clinic.models import ClinicProfile
from geopy.geocoders import Nominatim
from safar_saathi.utils import is_patient
import logging

logger = logging.getLogger(__name__)


@login_required
@user_passes_test(is_patient)
def dashboard(request):
    try:
        patient = request.user.patientprofile
        transfer_requests = TransferRequest.objects.filter(patient=patient)
        treatment_records = TreatmentRecord.objects.filter(
            patient=patient).order_by('-record_date')[:5]
        context = {
            'patient': patient,
            'transfer_requests': transfer_requests,
            'treatment_records': treatment_records,
        }
        return render(request, 'patient/dashboard.html', context)
    except PatientProfile.DoesNotExist:
        logger.error(f"Patient profile not found for user: {request.user.username}")
        messages.error(request, 'Your patient profile is missing. Please contact support.')
        return redirect('home')
    except Exception as e:
        logger.error(f"Error in patient dashboard: {str(e)}", exc_info=True)
        messages.error(request, 'An error occurred while loading your dashboard.')
        return redirect('home')


@login_required
@user_passes_test(is_patient)
def profile(request):
    try:
        patient = request.user.patientprofile
    except PatientProfile.DoesNotExist:
        logger.error(f"Patient profile not found for user: {request.user.username}")
        messages.error(request, 'Your patient profile is missing. Please contact support.')
        return redirect('home')

    if request.method == 'POST':
        # Update user fields
        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name = request.POST.get('last_name', '').strip()
        request.user.email = request.POST.get('email', '').strip()
        request.user.save()

        # Update patient profile fields
        patient.phone_number = request.POST.get('phone_number', '').strip()
        patient.address = request.POST.get('address', '').strip()
        patient.current_location = request.POST.get('current_location', '').strip()
        patient.consent_given = request.POST.get('consent_given') == 'on'
        patient.save()

        messages.success(request, 'Profile updated successfully.')
        return redirect('patient:profile')

    context = {
        'patient': patient,
    }
    return render(request, 'patient/profile.html', context)


@login_required
@user_passes_test(is_patient)
def transfer_request(request):
    try:
        patient = request.user.patientprofile
    except PatientProfile.DoesNotExist:
        logger.error(f"Patient profile not found for user: {request.user.username}")
        messages.error(request, 'Your patient profile is missing. Please contact support.')
        return redirect('home')

    if not patient.current_clinic:
        messages.error(request, 'You are not assigned to any clinic. Please contact admin.')
        return redirect('patient:dashboard')

    if request.method == 'POST':
        form = TransferRequestForm(request.POST, patient=patient)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Check if patient is not already requesting transfer to this clinic
                    to_clinic = form.cleaned_data['to_clinic']
                    existing_request = TransferRequest.objects.filter(
                        patient=patient,
                        to_clinic=to_clinic,
                        status__in=['pending', 'approved']
                    ).exists()

                    if existing_request:
                        messages.error(request, 'You already have a pending or approved transfer request to this clinic.')
                        return redirect('patient:transfer_request')

                    # Create transfer request
                    transfer_request = form.save(commit=False)
                    transfer_request.patient = patient
                    transfer_request.from_clinic = patient.current_clinic
                    transfer_request.status = 'pending'
                    transfer_request.save()

                    logger.info(f"Transfer request created: {patient.user.username} from {patient.current_clinic.name} to {to_clinic.name}")
                    messages.success(request, 'Transfer request submitted successfully.')
                    return redirect('patient:dashboard')

            except IntegrityError as e:
                logger.error(f"Database integrity error in transfer request: {str(e)}")
                messages.error(request, 'A database error occurred. Please try again.')
            except Exception as e:
                logger.error(f"Unexpected error in transfer request: {str(e)}", exc_info=True)
                messages.error(request, 'An unexpected error occurred. Please try again.')
        else:
            # Form validation errors will be displayed in the template
            pass
    else:
        form = TransferRequestForm(patient=patient)

    context = {
        'form': form,
    }
    return render(request, 'patient/transfer_request.html', context)


@login_required
@user_passes_test(is_patient)
def nearby_clinics(request):
    patient_lat = request.GET.get('lat')
    patient_lng = request.GET.get('lng')
    patient = request.user.patientprofile
    clinics = ClinicProfile.objects.filter(is_approved=True, is_active=True, latitude__isnull=False, longitude__isnull=False)
    
    # Get patient's diseases
    patient_diseases = set(TreatmentRecord.objects.filter(patient=patient).values_list('disease', flat=True))
    if not patient_diseases:
        patient_diseases = {'HIV'}  # Default
    
    # Filter clinics that treat patient's diseases
    relevant_clinics = []
    for clinic in clinics:
        clinic_diseases = set(d.strip().lower() for d in clinic.diseases_treated.split(',') if d.strip())
        if patient_diseases & clinic_diseases or not clinic.diseases_treated:  # If no diseases specified, assume general
            relevant_clinics.append(clinic)
    
    nearby_clinics = []
    current_clinic_list = []
    other_clinics = []
    
    if patient_lat and patient_lng:
        from geopy.distance import geodesic
        patient_loc = (float(patient_lat), float(patient_lng))
        for clinic in relevant_clinics:
            clinic_loc = (clinic.latitude, clinic.longitude)
            distance = geodesic(patient_loc, clinic_loc).km
            if distance <= 50:  # Within 50 km
                clinic.distance = round(distance, 2)
                if patient.current_clinic and clinic.id == patient.current_clinic.id:
                    current_clinic_list.append(clinic)
                else:
                    other_clinics.append(clinic)

        # Create map
        import folium
        m = folium.Map(location=[float(patient_lat), float(patient_lng)], zoom_start=12)
        folium.Marker([float(patient_lat), float(patient_lng)], popup='Your Current Location', icon=folium.Icon(color='blue')).add_to(m)
        for clinic in current_clinic_list + other_clinics:
            color = 'green' if clinic in current_clinic_list else 'red'
            folium.Marker([clinic.latitude, clinic.longitude], popup=f"{clinic.name} - {clinic.distance} km", icon=folium.Icon(color=color)).add_to(m)
        map_html = m._repr_html_()
    else:
        map_html = None
        # Still segregate without location
        for clinic in relevant_clinics:
            if patient.current_clinic and clinic.id == patient.current_clinic.id:
                current_clinic_list.append(clinic)
            else:
                other_clinics.append(clinic)

    context = {
        'current_clinics': current_clinic_list,
        'other_clinics': other_clinics,
        'patient': patient,
        'map_html': map_html,
    }
    return render(request, 'patient/nearby_clinics.html', context)


@login_required
@user_passes_test(is_patient)
def clinic_detail(request, clinic_id):
    try:
        clinic = get_object_or_404(ClinicProfile, id=clinic_id)
        patient = request.user.patientprofile

        # Check if this is the patient's current clinic
        is_current_clinic = patient.current_clinic and patient.current_clinic.id == clinic.id

        # Check if patient has pending transfer request to this clinic
        has_pending_transfer = TransferRequest.objects.filter(
            patient=patient,
            to_clinic=clinic,
            status__in=['pending', 'approved']
        ).exists()

        context = {
            'clinic': clinic,
            'is_current_clinic': is_current_clinic,
            'has_pending_transfer': has_pending_transfer,
        }
        return render(request, 'patient/clinic_detail.html', context)
    except PatientProfile.DoesNotExist:
        logger.error(f"Patient profile not found for user: {request.user.username}")
        messages.error(request, 'Your patient profile is missing. Please contact support.')
        return redirect('home')
    except Exception as e:
        logger.error(f"Error loading clinic detail for clinic {clinic_id}: {str(e)}", exc_info=True)
        messages.error(request, 'An error occurred while loading clinic details.')
        return redirect('patient:nearby_clinics')


@login_required
@user_passes_test(is_patient)
def emergency_trigger(request):
    if request.method == 'POST':
        clinic_id = request.POST.get('clinic')
        reason = request.POST.get('reason')
        if not clinic_id or not reason:
            messages.error(
                request, 'Please select a clinic and provide a reason.')
            return redirect('patient:emergency_trigger')
        # Create emergency access
        from emergency.models import EmergencyAccess
        clinic = get_object_or_404(ClinicProfile, id=clinic_id)
        EmergencyAccess.objects.create(
            patient=request.user.patientprofile,
            clinic=clinic,
            requested_by=request.user,
            reason=reason,
            is_active=True
        )
        messages.success(request, 'Emergency access triggered.')
        return redirect('patient:dashboard')
    clinics = ClinicProfile.objects.filter(is_approved=True, is_active=True)
    context = {
        'clinics': clinics,
    }
    return render(request, 'patient/emergency_trigger.html', context)


def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create user
                    from django.contrib.auth.models import User, Group
                    user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        password=form.cleaned_data['password'],
                        email=form.cleaned_data['email'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name']
                    )

                    patient_group, created = Group.objects.get_or_create(name='Patient')
                    user.groups.add(patient_group)

                    # Geocode the address with error handling
                    lat, lng = None, None
                    try:
                        geolocator = Nominatim(user_agent="safar_saathi", timeout=10)
                        full_address = f"{form.cleaned_data['address']}, {form.cleaned_data['current_location']}"
                        location_obj = geolocator.geocode(full_address)
                        if location_obj:
                            lat, lng = location_obj.latitude, location_obj.longitude
                        else:
                            messages.warning(request, 'Could not geocode your address. You can update it later.')
                    except Exception as e:
                        logger.warning(f"Geocoding failed for address: {full_address} - {str(e)}")
                        messages.warning(request, 'Could not geocode your address. You can update it later.')

                    # Create patient profile
                    PatientProfile.objects.create(
                        user=user,
                        date_of_birth=form.cleaned_data['date_of_birth'],
                        phone_number=form.cleaned_data['phone_number'],
                        address=form.cleaned_data['address'],
                        current_location=form.cleaned_data['current_location'],
                        latitude=lat,
                        longitude=lng,
                        consent_given=form.cleaned_data['consent_given']
                    )

                    logger.info(f"New patient registered: {user.username} ({user.email})")
                    login(request, user)
                    messages.success(request, 'Registration successful! Welcome to Safar-Saathi.')
                    return redirect('patient:dashboard')

            except IntegrityError as e:
                logger.error(f"Database integrity error during registration: {str(e)}")
                messages.error(request, 'Registration failed due to a database error. Please try again.')
            except Exception as e:
                logger.error(f"Unexpected error during registration: {str(e)}", exc_info=True)
                messages.error(request, 'An unexpected error occurred during registration. Please try again.')
        else:
            # Form validation errors are already handled by Django's form validation
            pass
    else:
        form = PatientRegistrationForm()

    return render(request, 'patient/register.html', {'form': form})


@login_required
@user_passes_test(is_patient)
def book_appointment(request):
    patient = request.user.patientprofile
    if not patient.current_clinic:
        messages.error(request, 'You are not assigned to any clinic. Please contact admin.')
        return redirect('patient:dashboard')

    if request.method == 'POST':
        appointment_date = request.POST['appointment_date']
        appointment_type = request.POST['appointment_type']
        notes = request.POST.get('notes', '')

        # Find available doctor (for simplicity, assign to clinic user)
        doctor = patient.current_clinic.user

        Appointment.objects.create(
            patient=patient,
            clinic=patient.current_clinic,
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_type=appointment_type,
            notes=notes
        )
        messages.success(request, 'Appointment booked successfully.')
        return redirect('patient:dashboard')

    context = {
        'patient': patient,
    }
    return render(request, 'patient/book_appointment.html', context)


@login_required
@user_passes_test(is_patient)
def my_appointments(request):
    patient = request.user.patientprofile
    appointments = Appointment.objects.filter(patient=patient).order_by('-appointment_date')
    context = {
        'appointments': appointments,
    }
    return render(request, 'patient/my_appointments.html', context)


@login_required
@user_passes_test(is_patient)
def my_counselling_sessions(request):
    patient = request.user.patientprofile
    sessions = CounsellingSession.objects.filter(patient=patient).order_by('-session_date')
    context = {
        'sessions': sessions,
    }
    return render(request, 'patient/my_counselling_sessions.html', context)


@login_required
@user_passes_test(is_patient)
def external_consultations(request):
    patient = request.user.patientprofile
    consultations = ExternalConsultation.objects.filter(patient=patient).order_by('-consultation_date')
    context = {
        'consultations': consultations,
    }
    return render(request, 'patient/external_consultations.html', context)


@login_required
@user_passes_test(is_patient)
def book_external_consultation(request):
    patient = request.user.patientprofile
    if not patient.current_clinic:
        messages.error(request, 'You must be registered with a clinic to book external consultations.')
        return redirect('patient:dashboard')

    if request.method == 'POST':
        clinic_id = request.POST['clinic_id']
        consultation_date = request.POST['consultation_date']
        consultation_type = request.POST['consultation_type']
        reason = request.POST['reason']
        current_location = request.POST['current_location']
        stay_type = request.POST['stay_type']

        requesting_clinic = ClinicProfile.objects.get(id=clinic_id)

        ExternalConsultation.objects.create(
            patient=patient,
            requesting_clinic=requesting_clinic,
            parent_clinic=patient.current_clinic,
            consultation_date=consultation_date,
            consultation_type=consultation_type,
            reason=reason,
            current_location=current_location,
            stay_type=stay_type
        )
        messages.success(request, 'External consultation request submitted.')
        return redirect('patient:external_consultations')

    # Find clinics that specialize in the patient's disease
    disease_clinics = ClinicProfile.objects.filter(
        diseases_treated__icontains=patient.disease,
        is_approved=True,
        is_active=True
    ).exclude(id=patient.current_clinic.id)

    context = {
        'patient': patient,
        'disease_clinics': disease_clinics,
    }
    return render(request, 'patient/book_external_consultation.html', context)


@login_required
@user_passes_test(is_patient)
def my_prescriptions(request):
    patient = request.user.patientprofile
    prescriptions = Prescription.objects.filter(patient=patient).order_by('-prescription_date')
    context = {
        'prescriptions': prescriptions,
    }
    return render(request, 'patient/my_prescriptions.html', context)


@login_required
@user_passes_test(is_patient)
def telemedicine_sessions(request):
    patient = request.user.patientprofile
    sessions = TelemedicineSession.objects.filter(patient=patient).order_by('-session_date')
    context = {
        'sessions': sessions,
    }
    return render(request, 'patient/telemedicine_sessions.html', context)


@login_required
@user_passes_test(is_patient)
def book_telemedicine_session(request):
    patient = request.user.patientprofile
    if not patient.current_clinic:
        messages.error(request, 'You must be registered with a clinic to book telemedicine sessions.')
        return redirect('patient:dashboard')

    if request.method == 'POST':
        doctor_id = request.POST['doctor_id']
        session_date = request.POST['session_date']
        session_type = request.POST['session_type']
        notes = request.POST.get('notes', '')

        doctor = User.objects.get(id=doctor_id)

        TelemedicineSession.objects.create(
            patient=patient,
            doctor=doctor,
            clinic=patient.current_clinic,
            session_date=session_date,
            session_type=session_type,
            notes=notes
        )
        messages.success(request, 'Telemedicine session booked successfully.')
        return redirect('patient:telemedicine_sessions')

    # Get doctors from the patient's clinic
    doctors = User.objects.filter(
        groups__name='Clinic',
        clinicprofile=patient.current_clinic
    )

    context = {
        'patient': patient,
        'doctors': doctors,
    }
    return render(request, 'patient/book_telemedicine.html', context)


@login_required
@user_passes_test(is_patient)
def health_metrics(request):
    patient = request.user.patientprofile
    metrics = HealthMetric.objects.filter(patient=patient).order_by('-recorded_at')[:50]
    context = {
        'metrics': metrics,
    }
    return render(request, 'patient/health_metrics.html', context)


@login_required
@user_passes_test(is_patient)
def add_health_metric(request):
    patient = request.user.patientprofile
    if request.method == 'POST':
        metric_type = request.POST['metric_type']
        value = request.POST['value']
        unit = request.POST.get('unit', '')
        source = request.POST['source']
        notes = request.POST.get('notes', '')

        HealthMetric.objects.create(
            patient=patient,
            metric_type=metric_type,
            value=value,
            unit=unit,
            source=source,
            notes=notes
        )
        messages.success(request, 'Health metric recorded successfully.')
        return redirect('patient:health_metrics')

    context = {
        'patient': patient,
    }
    return render(request, 'patient/add_health_metric.html', context)
