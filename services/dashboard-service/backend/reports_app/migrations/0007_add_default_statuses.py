from django.db import migrations


def add_default_statuses(apps, schema_editor):
    ReportStatus = apps.get_model('reports_app', 'ReportStatus')
    
    statuses = [
        {'name': 'Черновик', 'description': 'Отчёт в черновике'},
        {'name': 'На согласовании', 'description': 'Отчёт на согласовании'},
        {'name': 'Согласован', 'description': 'Отчёт согласован'},
        {'name': 'Отклонён', 'description': 'Отчёт отклонён'},
        {'name': 'Опубликован', 'description': 'Отчёт опубликован'},
    ]
    
    for status_data in statuses:
        ReportStatus.objects.create(**status_data)


class Migration(migrations.Migration):

    dependencies = [
        ('reports_app', '0006_add_report_status'),
    ]

    operations = [
        migrations.RunPython(add_default_statuses),
    ]
