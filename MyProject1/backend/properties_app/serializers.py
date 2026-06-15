from rest_framework import serializers
from .models import Property


class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = [
            'id', 'address', 'cadastral_number', 'district',
            'property_type', 'total_area', 'status',
            'renovation_status', 'build_year', 'floors', 'created_at'
        ]