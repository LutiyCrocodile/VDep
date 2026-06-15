from rest_framework import serializers
from .models import ReportStatus, ReportTemplate, Report, SharedReport, Comment
from .models import ReportStatus, ReportTemplate, Report, SharedReport, Comment, ExcelImportQueue


class ReportStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportStatus
        fields = ['id', 'name', 'description']


class ReportTemplateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = ReportTemplate
        fields = ['id', 'name', 'description', 'config', 'created_by', 'created_by_name',
                  'is_public', 'created_at', 'updated_at']


class ReportSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    status_name = serializers.CharField(source='status.name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)

    class Meta:
        model = Report
        fields = ['id', 'title', 'description', 'template', 'template_name',
                  'author', 'author_name', 'status', 'status_name',
                  'data', 'file_path', 'created_at', 'updated_at']


class SharedReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SharedReport
        fields = '__all__'


class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'report', 'user', 'user_name', 'parent_comment', 'content', 'created_at']

class ExcelImportQueueSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ExcelImportQueue
        fields = ['id', 'filename', 'user', 'user_name', 'status',
                  'raw_data', 'error_message', 'created_at', 'processed_at']