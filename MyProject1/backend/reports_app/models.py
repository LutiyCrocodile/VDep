from django.db import models
from django.conf import settings


class ReportStatus(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'report_statuses'

    def __str__(self):
        return self.name


class ReportTemplate(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название шаблона")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    config = models.JSONField(verbose_name="Конфигурация слайдов")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'report_templates'

    def __str__(self):
        return self.name


class Report(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    template = models.ForeignKey(ReportTemplate, on_delete=models.SET_NULL, null=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports')
    status = models.ForeignKey(ReportStatus, on_delete=models.SET_NULL, null=True)
    data = models.JSONField(blank=True, null=True)
    file_path = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reports'

    def __str__(self):
        return self.title


class SharedReport(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shared_by')
    shared_with_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shared_to')
    access_level = models.CharField(max_length=20, default='view')
    share_token = models.CharField(max_length=255, unique=True, blank=True, null=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shared_reports'


class Comment(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'comments'

    def __str__(self):
        return f"Комментарий от {self.user}"

class ExcelImportQueue(models.Model):
    filename = models.CharField(max_length=255, verbose_name="Исходный файл")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Кто загрузил")
    status = models.CharField(max_length=50, default='pending', verbose_name="Статус")
    raw_data = models.JSONField(blank=True, null=True, verbose_name="Сырые данные")
    error_message = models.TextField(blank=True, null=True, verbose_name="Ошибки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Обработан")

    class Meta:
        db_table = 'excel_import_queue'
        verbose_name = "Очередь импорта"
        verbose_name_plural = "Очередь импорта"

    def __str__(self):
        return f"{self.filename} — {self.status}"


