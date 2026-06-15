from django.contrib import admin
from .models import ReportStatus, ReportTemplate, Report, SharedReport, Comment

@admin.register(ReportStatus)
class ReportStatusAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description']

@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'is_public', 'created_by', 'created_at']

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'author', 'status', 'created_at']

@admin.register(SharedReport)
class SharedReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'report', 'owner', 'shared_with_user', 'access_level']

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'report', 'user', 'created_at']