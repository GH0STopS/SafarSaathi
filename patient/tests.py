from django.test import TestCase
from django.contrib.auth.models import User
from patient.forms import PatientRegistrationForm
from patient.models import PatientProfile

class PatientRegistrationFormTest(TestCase):
    def test_form_valid_data(self):
        """Test form with valid data"""
        form_data = {
            'username': 'testpatient',
            'email': 'patient@test.com',
            'password': 'TestPass123!',
            'confirm_password': 'TestPass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'phone_number': '+1234567890',
            'address': '123 Test Street, Test City',
            'current_location': 'Test City',
            'consent_given': True,
        }
        form = PatientRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form should be valid but got errors: {form.errors}")

    def test_form_invalid_email(self):
        """Test form with invalid email"""
        form_data = {
            'username': 'testpatient',
            'email': 'invalid-email',
            'password': 'TestPass123!',
            'confirm_password': 'TestPass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'phone_number': '+1234567890',
            'address': '123 Test Street, Test City',
            'current_location': 'Test City',
            'consent_given': True,
        }
        form = PatientRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_form_password_mismatch(self):
        """Test form with mismatched passwords"""
        form_data = {
            'username': 'testpatient',
            'email': 'patient@test.com',
            'password': 'TestPass123!',
            'confirm_password': 'DifferentPass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'phone_number': '+1234567890',
            'address': '123 Test Street, Test City',
            'current_location': 'Test City',
            'consent_given': True,
        }
        form = PatientRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)

    def test_form_missing_consent(self):
        """Test form with missing consent"""
        form_data = {
            'username': 'testpatient',
            'email': 'patient@test.com',
            'password': 'TestPass123!',
            'confirm_password': 'TestPass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'phone_number': '+1234567890',
            'address': '123 Test Street, Test City',
            'current_location': 'Test City',
            'consent_given': False,
        }
        form = PatientRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('consent_given', form.errors)
