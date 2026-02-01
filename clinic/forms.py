from django import forms
from django.contrib.auth.models import User
from .models import ClinicProfile, Disease
from patient.models import Appointment, TreatmentRecord, CounsellingSession
import re


def validate_password_strength(value):
    """Validate that password meets strength requirements."""
    if len(value) < 8:
        raise forms.ValidationError("Password must be at least 8 characters long.")
    
    if not re.search(r'[a-z]', value):
        raise forms.ValidationError("Password must contain at least one lowercase letter.")
    
    if not re.search(r'[A-Z]', value):
        raise forms.ValidationError("Password must contain at least one uppercase letter.")
    
    if not re.search(r'[0-9]', value):
        raise forms.ValidationError("Password must contain at least one number.")
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', value):
        raise forms.ValidationError("Password must contain at least one special character.")
    
    return value


class ClinicRegistrationForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150,
        min_length=3,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
    )
    password = forms.CharField(
        min_length=8,
        validators=[validate_password_strength],
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a strong password'
        })
    )
    confirm_password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'clinic.email@example.com'
        })
    )
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Clinic Name'
        })
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Full clinic address'
        })
    )
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1-234-567-8900'
        })
    )
    location = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City, State/Country'
        })
    )
    diseases_treated = forms.ModelMultipleChoiceField(
        queryset=Disease.objects.filter(is_active=True),
        required=False,
        widget=forms.MultipleHiddenInput(),  # Hidden inputs will be created by JavaScript
        help_text="Select one or more diseases that this clinic specializes in treating"
    )

    class Meta:
        model = ClinicProfile
        fields = ['name', 'address', 'phone_number', 'location', 'diseases_treated']

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise forms.ValidationError("Username can only contain letters, numbers, and underscores.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        # Basic phone number validation
        if not re.match(r'^[\+]?[1-9][\d]{0,15}$', phone_number.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')):
            raise forms.ValidationError("Please enter a valid phone number.")
        return phone_number

    def clean_name(self):
        name = self.cleaned_data['name']
        if len(name.strip()) < 2:
            raise forms.ValidationError("Clinic name must be at least 2 characters long.")
        return name.strip()

    def clean_address(self):
        address = self.cleaned_data['address']
        if len(address.strip()) < 10:
            raise forms.ValidationError("Please provide a complete address (at least 10 characters).")
        return address.strip()

    def clean_location(self):
        location = self.cleaned_data['location']
        if len(location.strip()) < 2:
            raise forms.ValidationError("Location must be at least 2 characters long.")
        return location.strip()

    def clean_diseases_treated(self):
        diseases = self.cleaned_data.get('diseases_treated')
        # Since required=False, diseases can be None or empty
        # We'll allow empty selection for now, but clinics should ideally select diseases
        return diseases or []

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data


class AppointmentForm(forms.ModelForm):
    appointment_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )
    reason = forms.CharField(
        max_length=200,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Reason for appointment'
        })
    )

    class Meta:
        model = Appointment
        fields = ['appointment_date', 'reason']

    def clean_appointment_date(self):
        appointment_date = self.cleaned_data['appointment_date']
        from django.utils import timezone
        now = timezone.now()

        if appointment_date < now:
            raise forms.ValidationError("Appointment date cannot be in the past.")

        # Check if appointment is within business hours (9 AM - 5 PM)
        if not (9 <= appointment_date.hour <= 17):
            raise forms.ValidationError("Appointments can only be scheduled between 9 AM and 5 PM.")

        # Check if it's a weekday
        if appointment_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            raise forms.ValidationError("Appointments can only be scheduled on weekdays.")

        return appointment_date


class TreatmentRecordForm(forms.ModelForm):
    disease = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Disease/Condition name'
        })
    )
    treatment_details = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Detailed treatment information'
        })
    )
    record_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    class Meta:
        model = TreatmentRecord
        fields = ['disease', 'treatment_details', 'record_date']

    def clean_disease(self):
        disease = self.cleaned_data['disease'].strip()
        if len(disease) < 2:
            raise forms.ValidationError("Disease name must be at least 2 characters long.")
        return disease

    def clean_record_date(self):
        record_date = self.cleaned_data['record_date']
        from datetime import date
        today = date.today()

        if record_date > today:
            raise forms.ValidationError("Record date cannot be in the future.")

        return record_date


class CounsellingSessionForm(forms.ModelForm):
    session_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Session notes and observations'
        })
    )

    class Meta:
        model = CounsellingSession
        fields = ['session_date', 'notes']

    def clean_session_date(self):
        session_date = self.cleaned_data['session_date']
        from django.utils import timezone
        now = timezone.now()

        if session_date < now:
            raise forms.ValidationError("Session date cannot be in the past.")

        return session_date