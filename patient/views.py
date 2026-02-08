from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponseBadRequest
from .models import MedicationIntake, PatientProfile, TransferRequest, TreatmentRecord, Appointment, CounsellingSession, ExternalConsultation, MedicalDataRequest, Prescription, MedicationReminder, TelemedicineSession, HealthMetric, Notification
from emergency.models import EmergencyAccess, EmergencyAlert
from .forms import PatientRegistrationForm, TransferRequestForm, AppointmentBookingForm
from clinic.models import ClinicProfile
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import folium
from safar_saathi.utils import is_patient
import logging
from datetime import date, timedelta, datetime

logger = logging.getLogger(__name__)


@login_required
@user_passes_test(is_patient)
def dashboard(request):
    try:
        patient = request.user.patientprofile
        transfer_requests = TransferRequest.objects.filter(patient=patient)
        treatment_records = TreatmentRecord.objects.filter(
            patient=patient).order_by('-record_date')[:5]
        unread_notifications = Notification.objects.filter(
            patient=patient, is_read=False).count()
        
        # # Calculate medication adherence for the last 30 days
        # from datetime import datetime, timedelta
        # thirty_days_ago = datetime.now() - timedelta(days=30)
        # medication_logs = MedicationIntake.objects.filter(
        #     reminder__prescription__patient=patient,
        #     scheduled_time__gte=thirty_days_ago
        # )
        
        # total_doses = medication_logs.count()
        # taken_doses = medication_logs.filter(was_taken=True).count()
        # adherence_percentage = (taken_doses / total_doses * 100) if total_doses > 0 else 100
        
       

        # Last 30 days range
        thirty_days_ago = date.today() - timedelta(days=30)

        medication_intakes = MedicationIntake.objects.filter(
            reminder__prescription__patient=patient,
            intake_date__gte=thirty_days_ago,
            reminder__is_active=True
        )

        total_doses = medication_intakes.count()
        taken_doses = medication_intakes.filter(has_taken=True).count()

        adherence_percentage = (
            round((taken_doses / total_doses) * 100, 2)
            if total_doses > 0
            else 100
        )

        
        # Get upcoming appointments
        upcoming_appointments = Appointment.objects.filter(
            patient=patient,
            appointment_date__gte=datetime.now(),
            status__in=['scheduled', 'confirmed']
        ).order_by('appointment_date')[:3]
        
        # Get recent prescriptions
        # recent_prescriptions = Prescription.objects.filter(
        #     patient=patient,
        #     is_active=True
        # ).order_by('-prescription_date')[:3]
        # prescription = Prescription.objects.filter(patient=patient, is_active=True).order_by('-prescription_date')
        
        medications = MedicationIntake.objects.filter(
            reminder__prescription__patient=patient,
            intake_date = timezone.now().date(),
            reminder__is_active=True
        ).order_by('-intake_date')
        
        context = {
            'patient': patient,
            'transfer_requests': transfer_requests,
            'treatment_records': treatment_records,
            'unread_count': unread_notifications,
            'adherence_percentage': round(adherence_percentage, 1),
            'upcoming_appointments': upcoming_appointments,
            'medications': medications,
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
    try:
        if request.method != 'GET':
            return HttpResponseBadRequest("Invalid request method")

        patient_lat = request.GET.get('lat')
        patient_lng = request.GET.get('lng')

        # Get patient safely
        try:
            patient = request.user.patientprofile
        except Exception:
            logger.error(f"Patient profile missing for user {request.user.username}")
            messages.error(request, "Patient profile not found.")
            return redirect('home')

        logger.info(
            f"Patient {request.user.username} searching nearby clinics "
            f"lat={patient_lat}, lng={patient_lng}"
        )
    
        # Fetch clinics safely
        clinics = ClinicProfile.objects.filter(
            is_approved=True,
            is_active=True,
            latitude__isnull=False,
            longitude__isnull=False
        )

        logger.info(
            f"Found {clinics.count()} approved clinics with location data {clinics}"
        )

        # Get patient diseases
        try:
            patient_diseases = set(
                TreatmentRecord.objects.filter(patient=patient)
                .values_list('disease', flat=True)
            )
            logger.info(
                f"Patient {request.user.username} has diseases: {patient_diseases}"
            )
        except Exception as e:
            logger.warning(f"Error fetching diseases: {e}")
            patient_diseases = set()

        if not patient_diseases:
            patient_diseases = {'HIV'}

        # Filter clinics by disease
        relevant_clinics = []
        logger.info(f"{clinics[0].name} treats diseases: {[d.name for d in clinics[0].diseases_treated.all()]}")
        for clinic in clinics:
            clinic_diseases = set(d.name for d in clinic.diseases_treated.all())
            # logger.debug(f"Clinic {clinic.name} treats diseases: {clinic_diseases}")
            if patient_diseases & clinic_diseases or not clinic_diseases:
                relevant_clinics.append(clinic)
        logger.info(
            f"Found {len(relevant_clinics)} relevant clinics for patient {request.user.username}"
        )
        current_clinic_list = []
        other_clinics = []

        map_html = None

        # Validate coordinates
        if patient_lat and patient_lng:
            try:
                patient_loc = (float(patient_lat), float(patient_lng))
            except (ValueError, TypeError):
                logger.warning("Invalid latitude or longitude received")
                messages.warning(request, "Invalid location coordinates.")
                patient_loc = None

            if patient_loc:
                for clinic in relevant_clinics:
                    try:
                        clinic_loc = (clinic.latitude, clinic.longitude)
                        distance = geodesic(patient_loc, clinic_loc).km

                        if distance <= 50:
                            clinic.distance = round(distance, 2)
                            if patient.current_clinic and clinic.id == patient.current_clinic.id:
                                current_clinic_list.append(clinic)
                            else:
                                other_clinics.append(clinic)

                    except Exception as e:
                        logger.warning(
                            f"Distance calculation failed for clinic {clinic.id}: {e}"
                        )

                # Create map safely
                try:
                    

                    m = folium.Map(
                        location=[patient_loc[0], patient_loc[1]],
                        zoom_start=12
                    )

                    folium.Marker(
                        [patient_loc[0], patient_loc[1]],
                        popup='Your Current Location',
                        icon=folium.Icon(color='blue')
                    ).add_to(m)

                    for clinic in current_clinic_list + other_clinics:
                        color = 'green' if clinic in current_clinic_list else 'red'
                        folium.Marker(
                            [clinic.latitude, clinic.longitude],
                            popup=f"{clinic.name} - {clinic.distance} km",
                            icon=folium.Icon(color=color)
                        ).add_to(m)

                    map_html = m._repr_html_()

                except Exception as e:
                    logger.error(f"Map generation failed: {e}")
                    messages.warning(
                        request,
                        "Map could not be loaded, showing clinics list only."
                    )

        else:
            # No location → list clinics only
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

    except Exception as e:
        logger.exception("Unexpected error in nearby_clinics view")
        messages.error(
            request,
            "Something went wrong while searching nearby clinics. Please try again."
        )
        return redirect('patient:dashboard')


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
        
        clinic = get_object_or_404(ClinicProfile, id=clinic_id)
        EmergencyAccess.objects.create(
            patient=request.user.patientprofile,
            clinic=clinic,
            requested_by=request.user,
            reason=reason,
            is_active=True
        )
        EmergencyAlert.objects.create(
            patient=request.user.patientprofile,
            alert_type='patient_triggered',
            alert_message=f"Emergency access triggered by {request.user.username} for clinic {clinic.name} with reason: {reason}",
            location_lat=request.user.patientprofile.latitude,
            location_lng=request.user.patientprofile.longitude,
            location_address=request.user.patientprofile.address
            )
        logger.info(f"Emergency access triggered by {request.user.username} for clinic {clinic.name} with reason: {reason}")
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
                        current_clinic=form.cleaned_data['current_clinic'],
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
        form = AppointmentBookingForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.patient = patient
            appointment.clinic = patient.current_clinic
            # appointment.doctor = patient.current_clinic.user  # Assign to clinic user
            appointment.save()
            messages.success(request, 'Appointment booked successfully.')
            return redirect('patient:my_appointments')
        else:
            logger.error(f"Appointment booking form errors: {form.errors}")
            messages.error(request, 'There was an error with your appointment form. Please check the details and try again.')
    else:
        form = AppointmentBookingForm()

    context = {
        'patient': patient,
        'form': form,
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
    
    # Add video session info for upcoming sessions
    upcoming_sessions = sessions.filter(session_date__gte=timezone.now(), status__in=['scheduled'])
    for session in upcoming_sessions:
        if session.session_mode == 'online' and session.meeting_link:
            session.can_join = True
        else:
            session.can_join = False
    
    context = {
        'sessions': sessions,
        'upcoming_sessions': upcoming_sessions,
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
        current_location = request.POST.get('current_location', '')
        stay_type = request.POST['stay_type']

        geolocator = Nominatim(user_agent="safar_saathi", timeout=10)
        try:
            patient_location = geolocator.geocode(current_location)
            parent_clinic = patient.current_clinic
            if patient_location and parent_clinic.latitude and parent_clinic.longitude:
                patient_coords = (patient_location.latitude, patient_location.longitude)
                clinic_coords = (parent_clinic.latitude, parent_clinic.longitude)
                distance = geodesic(patient_coords, clinic_coords).km
                if distance < 10:
                        messages.warning(request,"You appear to be near your registered clinic. External consultation is allowed only when you are in a different location.")
                        return redirect('patient:book_external_consultation')   
        except Exception as e:
            logger.warning(f"Geocoding failed for external consultation: {str(e)}")
            messages.warning(request, "Could not verify your location. Please ensure you are entering a valid address.")


        requesting_clinic = ClinicProfile.objects.get(id=clinic_id)

        ExternalConsultation.objects.create(
            patient=patient,
            requesting_clinic=requesting_clinic,
            parent_clinic= parent_clinic,
            consultation_date=consultation_date,
            consultation_type=consultation_type,
            reason=reason,
            current_location=current_location,
            stay_type=stay_type
        )
        messages.success(request, 'External consultation request submitted.')
        return redirect('patient:external_consultations')

    # Find clinics that specialize in the patient's disease
    disease = TreatmentRecord.objects.filter(patient=patient).values_list('disease', flat=True).first()
    disease_clinics = ClinicProfile.objects.filter(
        diseases_treated__name__icontains=disease if disease else '',
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


@login_required
@user_passes_test(is_patient)
def notifications(request):
    try:
        patient = request.user.patientprofile
        notifications = Notification.objects.filter(patient=patient).order_by('-created_at')
        unread_count = notifications.filter(is_read=False).count()
        
        context = {
            'notifications': notifications,
            'unread_count': unread_count,
        }
        return render(request, 'patient/notifications.html', context)
    except PatientProfile.DoesNotExist:
        logger.error(f"Patient profile not found for user: {request.user.username}")
        messages.error(request, 'Your patient profile is missing. Please contact support.')
        return redirect('home')
    except Exception as e:
        logger.error(f"Error in notifications view: {str(e)}", exc_info=True)
        messages.error(request, 'An error occurred while loading notifications.')
        return redirect('patient:dashboard')


@login_required
@user_passes_test(is_patient)
def mark_notification_read(request, notification_id):
    try:
        patient = request.user.patientprofile
        notification = get_object_or_404(Notification, id=notification_id, patient=patient)
        notification.is_read = True
        notification.save()
        messages.success(request, 'Notification marked as read.')
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}", exc_info=True)
        messages.error(request, 'An error occurred while updating the notification.')
    
    return redirect('patient:notifications')


@login_required
@user_passes_test(is_patient)
def mark_all_notifications_read(request):
    try:
        patient = request.user.patientprofile
        Notification.objects.filter(patient=patient, is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}", exc_info=True)
        messages.error(request, 'An error occurred while updating notifications.')
    
    return redirect('patient:notifications')

@login_required
@user_passes_test(is_patient)
def mark_medication_taken(request, medication_id):
    try:
        patient = request.user.patientprofile
        logger.info(f"Patient {request.user.username} marking medication {medication_id} as taken")
        # medicationR = get_object_or_404(MedicationReminder, id=medication_id, prescription__patient=patient)
        # medication = get_object_or_404(MedicationIntake, reminder = medicationR)
        medication = get_object_or_404(MedicationIntake, id=medication_id, reminder__prescription__patient=patient)
        medication.has_taken = True
        medication.taken_at = timezone.now()
        medication.save()
        messages.success(request, 'Medication marked as taken.')
    except Exception as e:
        logger.error(f"Error marking medication as taken: {str(e)}", exc_info=True)
        messages.error(request, 'An error occurred while updating the medication status.')
    
    return redirect('patient:dashboard')