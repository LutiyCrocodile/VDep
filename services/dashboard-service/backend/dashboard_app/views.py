from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Avg, Count
from django.db.models.functions import TruncMonth

from .models import MetricType, MetricsData
from .serializers import MetricTypeSerializer, MetricsDataSerializer


class MetricTypeViewSet(viewsets.ModelViewSet):
    queryset = MetricType.objects.all()
    serializer_class = MetricTypeSerializer
    permission_classes = [permissions.AllowAny]


class MetricsDataViewSet(viewsets.ModelViewSet):
    queryset = MetricsData.objects.all()
    serializer_class = MetricsDataSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Фильтрация по типу показателя
        metric_type_id = self.request.query_params.get('metric_type_id')
        if metric_type_id:
            queryset = queryset.filter(metric_type_id=metric_type_id)

        # Фильтрация по дате
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        # Фильтрация по району
        district = self.request.query_params.get('district')
        if district:
            queryset = queryset.filter(district=district)

        # Фильтрация по категории
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(metric_type__category=category)

        return queryset

    @action(detail=False, methods=['get'])
    def aggregated(self, request):
        """Агрегированные данные по районам"""
        metric_type_id = request.query_params.get('metric_type_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        queryset = self.get_queryset()

        # Группировка по районам
        if metric_type_id:
            queryset = queryset.filter(metric_type_id=metric_type_id)

        result = queryset.values('district').annotate(
            total=Sum('value'),
            avg=Avg('value'),
            count=Count('id')
        ).order_by('-total')

        return Response(list(result))

    @action(detail=False, methods=['get'])
    def by_month(self, request):
        """Динамика по месяцам"""
        metric_type_id = request.query_params.get('metric_type_id')

        queryset = self.get_queryset()
        if metric_type_id:
            queryset = queryset.filter(metric_type_id=metric_type_id)

        result = queryset.annotate(month=TruncMonth('date')).values('month').annotate(
            total=Sum('value')
        ).order_by('month')

        return Response(list(result))