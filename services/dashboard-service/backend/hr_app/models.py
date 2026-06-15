from django.db import models
from django.conf import settings

class HrEmployee(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    personnel_number = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=255)
    position = models.CharField(max_length=200, blank=True, null=True)
    department = models.CharField(max_length=200, blank=True, null=True)
    hire_date = models.DateField(blank=True, null=True)
    dismissal_date = models.DateField(blank=True, null=True)
    education = models.CharField(max_length=100, blank=True, null=True)
    qualification = models.CharField(max_length=200, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hr_employees'

    def __str__(self):
        return self.full_name