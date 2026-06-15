import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reports_app.models import ReportStatus

# Удаляем существующие статусы если есть
ReportStatus.objects.all().delete()

# Добавляем статусы по умолчанию
statuses = [
    {'name': 'Черновик', 'description': 'Отчёт в черновике'},
    {'name': 'На согласовании', 'description': 'Отчёт на согласовании'},
    {'name': 'Согласован', 'description': 'Отчёт согласован'},
    {'name': 'Отклонён', 'description': 'Отчёт отклонён'},
    {'name': 'Опубликован', 'description': 'Отчёт опубликован'},
]

for status_data in statuses:
    status, created = ReportStatus.objects.get_or_create(
        name=status_data['name'],
        defaults={'description': status_data['description']}
    )
    if created:
        print(f"Создан статус: {status.name}")
    else:
        print(f"Статус уже существует: {status.name}")

print("\nВсе статусы добавлены:")
for status in ReportStatus.objects.all():
    print(f"  - {status.name} (ID: {status.id})")
