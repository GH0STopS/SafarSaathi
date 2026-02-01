from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import PatientProfile, TransferRequest, Appointment
from clinic.models import ClinicProfile
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


class PatientRegistrationForm(forms.ModelForm):
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
            'placeholder': 'your.email@example.com'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1-234-567-8900'
        })
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Full address'
        })
    )
    current_location = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City, State/Country'
        })
    )
    consent_given = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    class Meta:
        model = PatientProfile
        fields = ['date_of_birth', 'phone_number', 'address', 'current_location', 'consent_given']

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

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data['date_of_birth']
        from datetime import date
        today = date.today()
        age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
        if age < 0:
            raise forms.ValidationError("Date of birth cannot be in the future.")
        if age > 150:
            raise forms.ValidationError("Please enter a valid date of birth.")
        return date_of_birth

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name']
        if len(first_name.strip()) < 1:
            raise forms.ValidationError("First name is required.")
        if not re.match(r'^[a-zA-Z\s]+$', first_name):
            raise forms.ValidationError("First name can only contain letters and spaces.")
        return first_name.strip()

    def clean_last_name(self):
        last_name = self.cleaned_data['last_name']
        if len(last_name.strip()) < 1:
            raise forms.ValidationError("Last name is required.")
        if not re.match(r'^[a-zA-Z\s]+$', last_name):
            raise forms.ValidationError("Last name can only contain letters and spaces.")
        return last_name.strip()

    def clean_address(self):
        address = self.cleaned_data['address']
        if len(address.strip()) < 10:
            raise forms.ValidationError("Please provide a complete address (at least 10 characters).")
        return address.strip()

    def clean_current_location(self):
        location = self.cleaned_data['current_location']
        if len(location.strip()) < 2:
            raise forms.ValidationError("Current location must be at least 2 characters long.")
        return location.strip()

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data


class TransferRequestForm(forms.ModelForm):
    to_clinic = forms.ModelChoiceField(
        queryset=ClinicProfile.objects.filter(is_approved=True),
        empty_label="Select a clinic",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    reason = forms.CharField(
        min_length=10,
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Please explain why you want to transfer to this clinic...'
        })
    )

    class Meta:
        model = TransferRequest
        fields = ['to_clinic', 'reason']

    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop('patient', None)
        super().__init__(*args, **kwargs)
        if self.patient and self.patient.current_clinic:
            self.fields['to_clinic'].queryset = self.fields['to_clinic'].queryset.exclude(
                id=self.patient.current_clinic.id
            )


class AppointmentBookingForm(forms.ModelForm):
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