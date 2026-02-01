from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('view', 'View'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('transfer', 'Transfer'),
        ('emergency', 'Emergency Access'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"
