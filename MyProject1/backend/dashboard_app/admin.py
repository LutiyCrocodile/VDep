from django.contrib import admin
from .models import MetricType, MetricsData

@admin.register(MetricType)
class MetricTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'unit', 'category']

@admin.register(MetricsData)
class MetricsDataAdmin(admin.ModelAdmin):
    list_display = ['id', 'metric_type', 'value', 'date', 'district']