from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from reports_app.views import (
    ReportStatusViewSet, ReportTemplateViewSet, ReportViewSet,
    SharedReportViewSet, CommentViewSet, ExcelImportViewSet,
)

from reports_app.views import (
    ReportStatusViewSet,
    ReportTemplateViewSet,
    ReportViewSet,
    SharedReportViewSet,
    CommentViewSet,
)
from users_app.views import UserViewSet, RoleViewSet
from dashboard_app.views import MetricTypeViewSet, MetricsDataViewSet
from properties_app.views import PropertyViewSet



router = DefaultRouter()
router.register(r'report-statuses', ReportStatusViewSet, basename='report-statuses')
router.register(r'report-templates', ReportTemplateViewSet, basename='report-templates')
router.register(r'reports', ReportViewSet, basename='reports')
router.register(r'shared-reports', SharedReportViewSet, basename='shared-reports')
router.register(r'comments', CommentViewSet, basename='comments')
router.register(r'users', UserViewSet, basename='users')
router.register(r'roles', RoleViewSet, basename='roles')
router.register(r'metric-types', MetricTypeViewSet, basename='metric-types')
router.register(r'metrics-data', MetricsDataViewSet, basename='metrics-data')
router.register(r'properties', PropertyViewSet, basename='properties')
router.register(r'excel-import', ExcelImportViewSet, basename='excel-import')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include(router.urls)),
]