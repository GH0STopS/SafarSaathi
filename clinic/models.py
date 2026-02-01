from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Disease(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, help_text="Optional description of the disease")
    is_active = models.BooleanField(default=True, help_text="Whether this disease is available for selection")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class ClinicProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone_number = models.CharField(max_length=15)
    location = models.CharField(max_length=100)  # City/State
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    diseases_treated = models.ManyToManyField(Disease, blank=True, help_text="Diseases treated by this clinic")
    is_approved = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, help_text="Whether this clinic is active")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name
