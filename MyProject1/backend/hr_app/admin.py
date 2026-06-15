from django.contrib import admin
from .models import HrEmployee

@admin.register(HrEmployee)
class HrEmployeeAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'personnel_number', 'department', 'position']