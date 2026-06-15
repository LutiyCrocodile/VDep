import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reports_app.models import Report
from dashboard_app.models import MetricsData, MetricType
from properties_app.models import Property

# Очистка старых данных
print("Очистка старых данных...")
MetricsData.objects.all().delete()
MetricType.objects.all().delete()
Property.objects.all().delete()
Report.objects.all().delete()
print("Старые данные очищены")

# Создание тестовых метрик
print("Создание тестовых метрик...")
metric_types = [
    {'name': 'Переселённые семьи', 'unit': 'семьи', 'category': 'Реновация'},
    {'name': 'Расселённые дома', 'unit': 'дома', 'category': 'Реновация'},
    {'name': 'Новые дома', 'unit': 'дома', 'category': 'Строительство'},
    {'name': 'Укомплектованность штата', 'unit': '%', 'category': 'Кадры'},
    {'name': 'Текучесть кадров', 'unit': '%', 'category': 'Кадры'},
    {'name': 'Обращения граждан', 'unit': 'шт', 'category': 'Обращения'},
    {'name': 'Сроки рассмотрения', 'unit': 'дни', 'category': 'Обращения'},
]

for mt_data in metric_types:
    metric_type, created = MetricType.objects.get_or_create(
        name=mt_data['name'],
        defaults={
            'unit': mt_data['unit'],
            'category': mt_data['category']
        }
    )
    if created:
        print(f"  Создан тип метрики: {metric_type.name}")

# Создание тестовых данных метрик по районам
print("Создание тестовых данных метрик...")
districts = ['ЦАО', 'САО', 'ЮАО', 'ВАО', 'ЗАО', 'СВАО', 'ЮВАО', 'ЗАО', 'СЗАО', 'ЮЗАО']

from datetime import date, timedelta

for metric_type in MetricType.objects.all():
    for district in districts:
        for day_offset in range(30):  # 30 дней данных
            metric_date = date.today() - timedelta(days=day_offset)
            
            value = 0
            if 'Переселённые семьи' in metric_type.name:
                value = 100 + (hash(district) % 50) + (day_offset % 10)
            elif 'Расселённые дома' in metric_type.name:
                value = 50 + (hash(district) % 30) + (day_offset % 5)
            elif 'Новые дома' in metric_type.name:
                value = 20 + (hash(district) % 15) + (day_offset % 3)
            elif 'Укомплектованность штата' in metric_type.name:
                value = 80 + (hash(district) % 15)
            elif 'Текучесть кадров' in metric_type.name:
                value = 5 + (hash(district) % 10)
            elif 'Обращения граждан' in metric_type.name:
                value = 200 + (hash(district) % 100) + (day_offset % 20)
            elif 'Сроки рассмотрения' in metric_type.name:
                value = 10 + (hash(district) % 15)
            
            MetricsData.objects.create(
                metric_type=metric_type,
                value=value,
                date=metric_date,
                district=district,
                department='ДГИ',
                source='Тестовые данные'
            )

print(f"Создано {MetricsData.objects.count()} записей метрик")

# Создание тестовых объектов недвижимости
print("Создание тестовых объектов недвижимости...")
districts = ['ЦАО', 'САО', 'ЮАО', 'ВАО', 'ЗАО', 'СВАО', 'ЮВАО', 'ЗАО', 'СЗАО', 'ЮЗАО']
property_types = ['жилое', 'нежилое', 'многоквартирное', 'индивидуальное']
statuses = ['эксплуатируется', 'на ремонте', 'в реновации', 'сносится']

for i in range(50):
    district = districts[i % len(districts)]
    cadastral_number = f"77:{(i // 10) + 1:02d}:000{(i % 10) + 1:04d}:{(i % 10) + 1:04d}"
    
    Property.objects.create(
        address=f"г. Москва, {district}, ул. Тестовая, д. {i + 1}",
        cadastral_number=cadastral_number,
        district=district,
        property_type=property_types[i % len(property_types)],
        total_area=50 + (i % 100) * 2,
        status=statuses[i % len(statuses)],
        renovation_status='в программе' if i % 3 == 0 else '',
        build_year=1950 + (i % 70),
        floors=5 + (i % 20)
    )

print(f"Создано {Property.objects.count()} объектов недвижимости")

# Создание тестового отчета
print("Создание тестового отчета...")
report = Report.objects.create(
    title='Тестовый отчет по реновации',
    description='Тестовый отчет для проверки функционала загрузки данных'
)
print(f"Создан отчет: {report.title} (ID: {report.id})")

print("\nГотово! Теперь нажмите кнопку 'ЗАГРУЗИТЬ ДАННЫЕ' для отчета ID:", report.id)
