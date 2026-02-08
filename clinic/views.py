from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.http import Http404
from .models import ClinicProfile
from .forms import ClinicRegistrationForm, AppointmentForm, TreatmentRecordForm, CounsellingSessionForm
from patient.models import MedicationIntake, PatientProfile, TransferRequest, TreatmentRecord, Appointment, CounsellingSession, ExternalConsultation, MedicalDataRequest, Prescription, MedicationReminder, TelemedicineSession, HealthMetric
from geopy.geocoders import Nominatim
from safar_saathi.utils import is_clinic_staff
import logging

logger = logging.getLogger(__name__)


def is_clinic(user):
    return user.groups.filter(name='Clinic').exists() and hasattr(user, 'clinicprofile')


def clinic_register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = ClinicRegistrationForm(request.POST)
        logger.info(f"Clinic registration POST data keys: {list(request.POST.keys())}")
        logger.info(f"Form is valid: {form.is_valid()}")
        if not form.is_valid():
            logger.error(f"Form errors: {form.errors}")
            logger.error(f"Non-field errors: {form.non_field_errors()}")
        if form.is_valid():
            logger.info("Form is valid, processing registration")
            try:
                with transaction.atomic():
                    # Create user
                    logger.info("Creating user...")
                    user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        password=form.cleaned_data['password'],
                        email=form.cleaned_data['email']
                    )
                    logger.info(f"User created: {user.username}")

                    clinic_group, created = Group.objects.get_or_create(name='Clinic')
                    user.groups.add(clinic_group)
                    logger.info(f"Added user to Clinic group")

                    # Geocode the address with improved error handling
                    lat, lng = None, None
                    try:
                        from geopy.geocoders import Nominatim
                        from geopy.exc import GeocoderTimedOut, GeocoderServiceError
                        geolocator = Nominatim(user_agent="safar_saathi_clinic_registration", timeout=15)
                        full_address = f"{form.cleaned_data['address']}, {form.cleaned_data['location']}"
                        
                        # Try geocoding with the full address
                        location_obj = geolocator.geocode(full_address)
                        
                        # If full address fails, try just the location
                        if not location_obj and form.cleaned_data['location']:
                            location_obj = geolocator.geocode(form.cleaned_data['location'])
                        
                        if location_obj:
                            lat, lng = location_obj.latitude, location_obj.longitude
                            logger.info(f"Successfully geocoded address for clinic: {full_address} -> ({lat}, {lng})")
                        else:
                            logger.warning(f"Could not geocode address: {full_address}")
                            messages.warning(request, 'Could not geocode your address. You can update it later in your profile.')
                    except (GeocoderTimedOut, GeocoderServiceError) as e:
                        logger.warning(f"Geocoding service error for address: {full_address} - {str(e)}")
                        messages.warning(request, 'Geocoding service is temporarily unavailable. You can update your location later.')
                    except Exception as e:
                        logger.warning(f"Unexpected geocoding error for address: {full_address} - {str(e)}")
                        messages.warning(request, 'Could not geocode your address. You can update it later in your profile.')

                    # Create clinic profile (without many-to-many field)
                    logger.info("Creating clinic profile...")
                    clinic = ClinicProfile.objects.create(
                        user=user,
                        name=form.cleaned_data['name'],
                        address=form.cleaned_data['address'],
                        phone_number=form.cleaned_data['phone_number'],
                        location=form.cleaned_data['location'],
                        latitude=lat,
                        longitude=lng
                    )
                    logger.info(f"Clinic profile created: {clinic.id}")

                    # Set many-to-many relationship
                    diseases = form.cleaned_data.get('diseases_treated') or []
                    logger.info(f"Diseases selected: {diseases} (type: {type(diseases)})")
                    if diseases:
                        try:
                            clinic.diseases_treated.set(diseases)
                            logger.info(f"Set {len(diseases)} diseases for clinic {clinic.name}")
                        except Exception as e:
                            logger.error(f"Error setting diseases: {e}")
                            raise
                    else:
                        logger.info("No diseases selected")

                    logger.info(f"New clinic registered: {user.username} ({user.email}) - {form.cleaned_data['name']}")
                    messages.success(request, 'Clinic registration submitted for approval! You will be notified once approved.')
                    return redirect('home')

            except IntegrityError as e:
                logger.error(f"Database integrity error during clinic registration: {str(e)}")
                messages.error(request, 'Registration failed due to a database error. Please try again.')
            except Exception as e:
                logger.error(f"Unexpected error during clinic registration: {str(e)}", exc_info=True)
                messages.error(request, 'An unexpected error occurred during registration. Please try again.')
        else:
            # Form validation errors will be displayed in the template
            pass
    else:
        form = ClinicRegistrationForm()

    return render(request, 'clinic/register.html', {'form': form})


@login_required
@user_passes_test(is_clinic)
def clinic_dashboard(request):
    try:
        clinic = request.user.clinicprofile
    except ClinicProfile.DoesNotExist:
        messages.error(request, 'Clinic profile not found.')
        return redirect('home')

    transfer_requests = TransferRequest.objects.filter(to_clinic=clinic)
    treatment_records = TreatmentRecord.objects.filter(
        clinic=clinic).order_by('-record_date')[:5]

    context = {
        'clinic': clinic,
        'transfer_requests': transfer_requests,
        'treatment_records': treatment_records,
    }
    return render(request, 'clinic/dashboard.html', context)


@login_required
@user_passes_test(is_clinic)
def clinic_profile(request):
    try:
        clinic = request.user.clinicprofile
    except ClinicProfile.DoesNotExist:
        messages.error(request, 'Clinic profile not found.')
        return redirect('home')

    if request.method == 'POST':
        # Update user fields
        request.user.email = request.POST.get('email', '').strip()
        request.user.save()

        # Update clinic profile fields
        clinic.name = request.POST.get('name', '').strip()
        clinic.address = request.POST.get('address', '').strip()
        clinic.phone_number = request.POST.get('phone_number', '').strip()
        clinic.location = request.POST.get('location', '').strip()
        
        # Handle diseases - this would need to be updated based on the multi-select
        # For now, we'll keep it simple
        clinic.save()

        messages.success(request, 'Profile updated successfully.')
        return redirect('clinic:profile')

    context = {
        'clinic': clinic,
    }
    return render(request, 'clinic/profile.html', context)


@login_required
@user_passes_test(is_clinic)
def clinic_transfer_request(request):
    clinic = request.user.clinicprofile
    if request.method == 'POST':
        try:
            patient_id = request.POST['patient']
            to_clinic_id = request.POST['to_clinic']
            reason = request.POST['reason']
            patient = PatientProfile.objects.get(id=patient_id)
            to_clinic = ClinicProfile.objects.get(id=to_clinic_id)

            # Check if patient is not already requesting transfer to this clinic
            existing_request = TransferRequest.objects.filter(
                patient=patient,
                to_clinic=to_clinic,
                status__in=['pending', 'approved']
            ).exists()

            if existing_request:
                messages.error(request, 'This patient already has a pending or approved transfer request to the selected clinic.')
                return redirect('clinic:clinic_transfer_request')

            TransferRequest.objects.create(
                patient=patient,
                from_clinic=clinic,
                to_clinic=to_clinic,
                reason=reason,
                status='pending'
            )
            messages.success(request, 'Transfer request submitted successfully!')
            return redirect('clinic:clinic_dashboard')
        except (PatientProfile.DoesNotExist, ClinicProfile.DoesNotExist, KeyError) as e:
            logger.error(f"Error in clinic transfer request: {str(e)}")
            messages.error(request, 'Invalid patient or clinic selected.')
            return redirect('clinic:clinic_transfer_request')
        except Exception as e:
            logger.error(f"Unexpected error in clinic transfer request: {str(e)}", exc_info=True)
            messages.error(request, 'An unexpected error occurred. Please try again.')
            return redirect('clinic:clinic_transfer_request')

    patients = PatientProfile.objects.filter(current_clinic=clinic)
    clinics = ClinicProfile.objects.exclude(id=clinic.id)
    context = {'patients': patients, 'clinics': clinics}
    return render(request, 'clinic/transfer_request.html', context)


@login_required
@user_passes_test(is_clinic)
def approve_transfer(request, request_id):
    transfer = TransferRequest.objects.get(id=request_id)
    if transfer.to_clinic == request.user.clinicprofile:
        transfer.status = 'approved'
        transfer.save()
        transfer.patient.current_clinic = transfer.to_clinic
        transfer.patient.save()
        messages.success(request, 'Transfer approved!')
    return redirect('clinic:clinic_dashboard')


@login_required
@user_passes_test(is_clinic)
def reject_transfer(request, request_id):
    transfer = TransferRequest.objects.get(id=request_id)
    if transfer.to_clinic == request.user.clinicprofile:
        transfer.status = 'rejected'
        transfer.save()
        messages.success(request, 'Transfer rejected!')
    return redirect('clinic:clinic_dashboard')

# @login_required
# @user_passes_test(is_clinic)
# def create_prescription(request):
#     clinic = request.user.clinicprofile
#     if request.method == 'POST':
#         patient_id = request.POST['patient']
#         diagnosis = request.POST['diagnosis']
#         medications = request.POST.getlist('medications[]')
#         dosages = request.POST.getlist('dosages[]')
#         instructions = request.POST.get('instructions', '')
#         follow_up_date = request.POST.get('follow_up_date')

#         patient = PatientProfile.objects.get(id=patient_id)

#         # Create prescription with medications as JSON
#         meds_list = []
#         for i in range(len(medications)):
#             if i < len(dosages):
#                 meds_list.append({
#                     'name': medications[i],
#                     'dosage': dosages[i]
#                 })

#         prescription = Prescription.objects.create(
#             patient=patient,
#             clinic=clinic,
#             doctor=request.user,
#             diagnosis=diagnosis,
#             medications=meds_list,
#             instructions=instructions,
#             follow_up_date=follow_up_date if follow_up_date else None
#         )

#         messages.success(request, 'Prescription created successfully.')
#         return redirect('clinic:manage_prescriptions')

#     patients = PatientProfile.objects.filter(current_clinic=clinic)
#     context = {
#         'patients': patients,
#     }
#     return render(request, 'clinic/create_prescription.html', context)

@login_required
@user_passes_test(is_clinic)
def add_treatment_record(request):
    clinic = request.user.clinicprofile

    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        disease = request.POST.get('disease')
        details = request.POST.get('details')

        # Prescription fields (optional)
        diagnosis = request.POST.get('diagnosis', '').strip()
        medications = request.POST.getlist('medications[]')
        dosages = request.POST.getlist('dosages[]')
        instructions = request.POST.get('instructions', '').strip()
        follow_up_date = request.POST.get('follow_up_date')
        frequency = request.POST.get('frequency', 'once daily')
        intake_times = request.POST.getlist('intake_times[]')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        patient = get_object_or_404(PatientProfile, id=patient_id)

        with transaction.atomic():
            # -------------------------------
            # 1. Create Treatment Record
            # -------------------------------
            TreatmentRecord.objects.create(
                patient=patient,
                clinic=clinic,
                disease=disease,
                details=details
            )

            # -------------------------------
            # 2. Build medications JSON
            # -------------------------------
            meds_list = []
            for i in range(len(medications)):
                med_name = medications[i].strip()
                dosage = dosages[i].strip() if i < len(dosages) else ''
                frequency = frequency if i < len(frequency) else 'once daily'
                intake_time = intake_times[i].strip() if i < len(intake_times) else '09:00'
                start_date_val = start_date if i < len(start_date) else timezone.now().date()
                end_date_val = end_date if i < len(end_date) else None
                

                if med_name:  # ignore empty rows
                    meds_list.append({
                        'name': med_name,
                        'dosage': dosage
                    })

            # -------------------------------
            # 3. Create Prescription ONLY if valid
            # -------------------------------
            if diagnosis and meds_list:
                prescription = Prescription.objects.create(
                    patient=patient,
                    clinic=clinic,
                    doctor=request.user,
                    diagnosis=diagnosis,
                    medications=meds_list,
                    instructions=instructions,
                    follow_up_date=follow_up_date or None
                )

                # -------------------------------
                # 4. (Optional but Recommended)
                # Auto-create Medication Reminders
                # -------------------------------
                for med in meds_list:
                    medicationR = MedicationReminder.objects.create(
                        prescription=prescription,
                        medication_name=med['name'],
                        dosage=med['dosage'],
                        frequency=frequency,  # can be extended later
                        
                        start_date=start_date_val,
                        end_date=end_date_val
                    )
                    times = intake_times[i].split(',')
                    for time in times:
                        MedicationIntake.objects.create(
                            reminder=medicationR,
                            intake_time=datetime.strptime(time.strip(), '%H:%M').time()
                        )

        messages.success(request, 'Treatment record added successfully.')
        return redirect('clinic:clinic_dashboard')

    patients = PatientProfile.objects.filter(current_clinic=clinic)
    return render(request, 'clinic/add_treatment.html', {'patients': patients})


@login_required
@user_passes_test(is_clinic)
def manage_appointments(request):
    clinic = request.user.clinicprofile
    appointments = Appointment.objects.filter(clinic=clinic).order_by('-appointment_date')
    context = {
        'appointments': appointments,
    }
    return render(request, 'clinic/manage_appointments.html', context)


@login_required
@user_passes_test(is_clinic)
def update_appointment_status(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, clinic=request.user.clinicprofile)
    if request.method == 'POST':
        status = request.POST['status']
        notes = request.POST.get('notes', '')
        meeting_link = request.POST.get('meeting_link', '')
        meeting_id = request.POST.get('meeting_id', '')
        meeting_password = request.POST.get('meeting_password', '')

        appointment.status = status
        if notes:
            appointment.notes += f"\n{notes}"
        if meeting_link:
            appointment.meeting_link = meeting_link
        if meeting_id:
            appointment.meeting_id = meeting_id
        if meeting_password:
            appointment.meeting_password = meeting_password
        appointment.save()

        # If appointment is completed, update treatment record
        if status == 'completed':
            TreatmentRecord.objects.create(
                patient=appointment.patient,
                clinic=appointment.clinic,
                disease=appointment.patient.disease,
                details=f"Appointment completed: {appointment.appointment_type}. Notes: {appointment.notes}",
                is_emergency=(appointment.appointment_type == 'emergency')
            )

        messages.success(request, f'Appointment status updated to {status}.')
    return redirect('clinic:manage_appointments')


@login_required
@user_passes_test(is_clinic)
def manage_counselling_sessions(request):
    clinic = request.user.clinicprofile
    sessions = CounsellingSession.objects.filter(clinic=clinic).order_by('-session_date')
    context = {
        'sessions': sessions,
    }
    return render(request, 'clinic/manage_counselling_sessions.html', context)


@login_required
@user_passes_test(is_clinic)
def schedule_counselling_session(request):
    clinic = request.user.clinicprofile
    if request.method == 'POST':
        patient_id = request.POST['patient']
        session_date = request.POST['session_date']
        session_type = request.POST['session_type']
        notes = request.POST.get('notes', '')

        patient = PatientProfile.objects.get(id=patient_id)
        CounsellingSession.objects.create(
            patient=patient,
            clinic=clinic,
            counsellor=request.user,
            session_date=session_date,
            session_type=session_type,
            notes=notes
        )
        messages.success(request, 'Counselling session scheduled.')
        return redirect('clinic:manage_counselling_sessions')

    patients = PatientProfile.objects.filter(current_clinic=clinic)
    context = {
        'patients': patients,
    }
    return render(request, 'clinic/schedule_counselling.html', context)


@login_required
@user_passes_test(is_clinic)
def update_counselling_session(request, session_id):
    session = get_object_or_404(CounsellingSession, id=session_id, clinic=request.user.clinicprofile)
    if request.method == 'POST':
        status = request.POST['status']
        medical_updates = request.POST.get('medical_updates', '')
        notes = request.POST.get('notes', '')
        follow_up_required = request.POST.get('follow_up_required') == 'on'
        follow_up_date = request.POST.get('follow_up_date') if follow_up_required else None

        session.status = status
        session.medical_updates = medical_updates
        if notes:
            session.notes += f"\n{notes}"
        session.follow_up_required = follow_up_required
        session.follow_up_date = follow_up_date
        session.save()

        # If session completed and has medical updates, create treatment record
        if status == 'completed' and medical_updates:
            TreatmentRecord.objects.create(
                patient=session.patient,
                clinic=session.clinic,
                disease=session.patient.disease,
                details=f"Counselling session completed. Medical updates: {medical_updates}",
                is_emergency=False
            )

        messages.success(request, f'Counselling session updated.')
    return redirect('clinic:manage_counselling_sessions')


@login_required
@user_passes_test(is_clinic)
def external_consultations(request):
    clinic = request.user.clinicprofile
    # Consultations where this clinic is the requesting clinic
    requested_consultations = ExternalConsultation.objects.filter(requesting_clinic=clinic).order_by('-consultation_date')
    # Consultations where this clinic is the parent clinic
    parent_consultations = ExternalConsultation.objects.filter(parent_clinic=clinic).order_by('-consultation_date')
    logger.info(f"External consultations - Requested: {requested_consultations.count()}, Parent: {parent_consultations.count()}")
    context = {
        'requested_consultations': requested_consultations,
        'parent_consultations': parent_consultations,
    }
    logger.info(f"{parent_consultations[0].requesting_clinic.name if parent_consultations else 'No requested consultations'} - {parent_consultations[0].parent_clinic.name if parent_consultations else 'No parent consultations'}")
    logger.info(f"user {parent_consultations[0].patient.user.get_full_name() if parent_consultations else 'No parent consultations'}")
    return render(request, 'clinic/external_consultations.html', context)


@login_required
@user_passes_test(is_clinic)
def approve_external_consultation(request, consultation_id):
    consultation = get_object_or_404(ExternalConsultation, id=consultation_id, parent_clinic=request.user.clinicprofile)
    if request.method == 'POST':
        consultation.status = 'approved'
        consultation.medical_data_access_granted = True
        consultation.grant_medical_access()
        consultation.save()

        # Create medical data request automatically
        MedicalDataRequest.objects.create(
            requesting_clinic=consultation.requesting_clinic,
            patient=consultation.patient,
            parent_clinic=consultation.parent_clinic,
            request_reason=f"External consultation: {consultation.reason}",
            requested_data_types=['treatment_records', 'prescriptions', 'test_results'],
            access_duration='one_time' if consultation.stay_type == 'temporary' else 'permanent'
        )

        messages.success(request, 'External consultation approved and medical data access granted.')
    return redirect('clinic:external_consultations')


@login_required
@user_passes_test(is_clinic)
def medical_data_requests(request):
    clinic = request.user.clinicprofile
    # Requests where this clinic is the parent clinic (receiving requests)
    received_requests = MedicalDataRequest.objects.filter(parent_clinic=clinic).order_by('-created_at')
    # Requests where this clinic is requesting data
    sent_requests = MedicalDataRequest.objects.filter(requesting_clinic=clinic).order_by('-created_at')
    logger.info(f"Medical data requests - Received: {received_requests.count()}, Sent: {sent_requests.count()}")
    context = {
        'received_requests': received_requests,
        'sent_requests': sent_requests,
    }
    return render(request, 'clinic/medical_data_requests.html', context)


@login_required
@user_passes_test(is_clinic)
def approve_medical_data_request(request, request_id):
    data_request = get_object_or_404(MedicalDataRequest, id=request_id, parent_clinic=request.user.clinicprofile)
    if request.method == 'POST':
        access_days = request.POST.get('access_days')
        data_request.approve_request(request.user, int(access_days) if access_days else None)
        messages.success(request, 'Medical data access approved.')
    return redirect('clinic:medical_data_requests')


@login_required
@user_passes_test(is_clinic)
def deny_medical_data_request(request, request_id):
    data_request = get_object_or_404(MedicalDataRequest, id=request_id, parent_clinic=request.user.clinicprofile)
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        data_request.deny_request(request.user, reason)
        messages.success(request, 'Medical data request denied.')
    return redirect('clinic:medical_data_requests')


@login_required
@user_passes_test(is_clinic)
def manage_prescriptions(request):
    clinic = request.user.clinicprofile
    prescriptions = Prescription.objects.filter(clinic=clinic).order_by('-prescription_date')
    context = {
        'prescriptions': prescriptions,
    }
    return render(request, 'clinic/manage_prescriptions.html', context)





@login_required
@user_passes_test(is_clinic)
def update_prescription(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id, clinic=request.user.clinicprofile)
    if request.method == 'POST':
        status = request.POST['status']
        prescription.status = status
        prescription.save()
        messages.success(request, f'Prescription status updated to {status}.')
    return redirect('clinic:manage_prescriptions')


@login_required
@user_passes_test(is_clinic)
def telemedicine_management(request):
    clinic = request.user.clinicprofile
    sessions = TelemedicineSession.objects.filter(clinic=clinic).order_by('-session_date')
    context = {
        'sessions': sessions,
    }
    return render(request, 'clinic/telemedicine_management.html', context)


@login_required
@user_passes_test(is_clinic)
def update_telemedicine_session(request, session_id):
    session = get_object_or_404(TelemedicineSession, id=session_id, clinic=request.user.clinicprofile)
    if request.method == 'POST':
        status = request.POST['status']
        meeting_link = request.POST.get('meeting_link', '')
        notes = request.POST.get('notes', '')
        duration = request.POST.get('duration_minutes')

        session.status = status
        if meeting_link:
            session.meeting_link = meeting_link
        if notes:
            session.notes += f"\n{notes}"
        if duration:
            session.duration_minutes = int(duration)
        session.save()

        messages.success(request, f'Telemedicine session updated.')
    return redirect('clinic:telemedicine_management')
