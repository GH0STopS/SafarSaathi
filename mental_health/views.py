from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from patient.models import CounsellingSession
from safar_saathi.utils import is_patient


@login_required
@user_passes_test(is_patient)
def mental_health_dashboard(request):
    # Filter counselling sessions that are mental health related
    sessions = CounsellingSession.objects.filter(
        patient__user=request.user,
        session_type__in=['individual', 'group', 'family', 'crisis']
    ).order_by('-session_date')
    context = {
        'sessions': sessions,
    }
    return render(request, 'mental_health/dashboard.html', context)


@login_required
@user_passes_test(is_patient)
def request_session(request):
    if request.method == 'POST':
        # Create a counselling session request
        CounsellingSession.objects.create(
            patient=request.user.patientprofile,
            clinic=request.user.patientprofile.current_clinic,
            counsellor=None,  # Will be assigned later
            session_date=request.POST.get('session_date'),
            status='requested',
            session_type=request.POST.get('session_type', 'individual'),
            notes=request.POST.get('notes', '')
        )
        messages.success(request, 'Session requested successfully!')
    return redirect('mental_health:mental_health_dashboard')
