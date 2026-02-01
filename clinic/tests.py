from django.test import TestCase
from django.contrib.auth.models import User
from clinic.forms import ClinicRegistrationForm
from clinic.models import ClinicProfile, Disease

class ClinicRegistrationFormTest(TestCase):
    def setUp(self):
        # Create some test diseases
        self.disease1 = Disease.objects.create(name="Diabetes")
        self.disease2 = Disease.objects.create(name="Hypertension")

    def test_form_valid_data(self):
        """Test form with valid data"""
        form_data = {
            'username': 'testclinic',
            'email': 'clinic@test.com',
            'password': 'TestPass123!',
            'confirm_password': 'TestPass123!',
            'name': 'Test Clinic',
            'phone_number': '+1234567890',
            'address': '123 Test Street, Test City',
            'location': 'Test City',
            'diseases_treated': [self.disease1.id, self.disease2.id],
        }
        form = ClinicRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form should be valid but got errors: {form.errors}")

    def test_form_invalid_email(self):
        """Test form with invalid email"""
        form_data = {
            'username': 'testclinic',
            'email': 'invalid-email',
            'password': 'TestPass123!',
            'confirm_password': 'TestPass123!',
            'name': 'Test Clinic',
            'phone_number': '+1234567890',
            'address': '123 Test Street, Test City',
            'location': 'Test City',
            'diseases_treated': [self.disease1.id],
        }
        form = ClinicRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_form_password_mismatch(self):
        """Test form with mismatched passwords"""
        form_data = {
            'username': 'testclinic',
            'email': 'clinic@test.com',
            'password': 'TestPass123!',
            'confirm_password': 'DifferentPass123!',
            'name': 'Test Clinic',
            'phone_number': '+1234567890',
            'address': '123 Test Street, Test City',
            'location': 'Test City',
            'diseases_treated': [self.disease1.id],
        }
        form = ClinicRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
