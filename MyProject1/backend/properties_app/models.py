from django.db import models

class Property(models.Model):
    address = models.CharField(max_length=500)
    cadastral_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    property_type = models.CharField(max_length=50, blank=True, null=True)
    total_area = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    renovation_status = models.CharField(max_length=50, blank=True, null=True)
    build_year = models.IntegerField(blank=True, null=True)
    floors = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'properties'

    def __str__(self):
        return self.address