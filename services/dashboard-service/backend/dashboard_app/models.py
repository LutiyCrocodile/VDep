from django.db import models

class MetricType(models.Model):
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=20, blank=True, null=True)
    category = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'metric_types'

    def __str__(self):
        return self.name


class MetricsData(models.Model):
    metric_type = models.ForeignKey(MetricType, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()
    district = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=200, blank=True, null=True)
    source = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'metrics_data'
        indexes = [
            models.Index(fields=['metric_type', 'date', 'district']),
        ]

    def __str__(self):
        return f"{self.metric_type.name}: {self.value} ({self.date})"