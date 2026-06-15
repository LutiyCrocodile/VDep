from rest_framework import serializers
from .models import MetricType, MetricsData


class MetricTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricType
        fields = ['id', 'name', 'unit', 'category']


class MetricsDataSerializer(serializers.ModelSerializer):
    metric_name = serializers.CharField(source='metric_type.name', read_only=True)
    metric_unit = serializers.CharField(source='metric_type.unit', read_only=True)
    metric_category = serializers.CharField(source='metric_type.category', read_only=True)

    class Meta:
        model = MetricsData
        fields = ['id', 'metric_type', 'metric_name', 'metric_unit', 'metric_category',
                  'value', 'date', 'district', 'department', 'source', 'created_at']