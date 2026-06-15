from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count

from .models import Property
from .serializers import PropertySerializer


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        district = self.request.query_params.get('district')
        if district:
            queryset = queryset.filter(district=district)

        property_type = self.request.query_params.get('property_type')
        if property_type:
            queryset = queryset.filter(property_type=property_type)

        renovation_status = self.request.query_params.get('renovation_status')
        if renovation_status:
            queryset = queryset.filter(renovation_status=renovation_status)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(address__icontains=search)

        return queryset

    @action(detail=False, methods=['get'])
    def stats(self, request):
        total = Property.objects.count()

        by_district = Property.objects.values('district').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        by_renovation = Property.objects.values('renovation_status').annotate(
            count=Count('id')
        )

        by_type = Property.objects.values('property_type').annotate(
            count=Count('id')
        )

        return Response({
            'total': total,
            'by_district': list(by_district),
            'by_renovation': list(by_renovation),
            'by_type': list(by_type),
        })