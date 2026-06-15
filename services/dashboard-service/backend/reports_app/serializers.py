from rest_framework import serializers
from .models import ReportStatus, ReportTemplate, Report, SharedReport, Comment
from .models import ReportStatus, ReportTemplate, Report, SharedReport, Comment, ExcelImportQueue


class ReportStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportStatus
        fields = ['id', 'name', 'description']


class ReportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportTemplate
        fields = ['id', 'name', 'description', 'config', 'is_public', 'created_at', 'updated_at']


class ReportSerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(source='status.name', read_only=True, allow_null=True)

    class Meta:
        model = Report
        fields = ['id', 'title', 'description', 'data', 'file_path', 'status', 'status_name', 'created_at', 'updated_at']


class SharedReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SharedReport
        fields = '__all__'


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'report', 'parent_comment', 'content', 'created_at']

class ExcelImportQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcelImportQueue
        fields = ['id', 'filename', 'status',
                  'raw_data', 'error_message', 'created_at', 'processed_at']