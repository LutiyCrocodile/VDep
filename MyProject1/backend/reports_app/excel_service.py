import openpyxl
from datetime import datetime
from django.utils import timezone
from dashboard_app.models import MetricsData, MetricType
from properties_app.models import Property


class ExcelImporter:
    """Сервис для импорта данных из Excel-файлов"""

    @staticmethod
    def parse_file(file_path, sheet_name=None):
        """Читает Excel-файл и возвращает список словарей"""
        workbook = openpyxl.load_workbook(file_path, data_only=True)

        if sheet_name:
            sheet = workbook[sheet_name]
        else:
            sheet = workbook.active

        rows = []
        headers = []

        for i, row in enumerate(sheet.iter_rows(values_only=True)):
            if i == 0:
                headers = [str(h).strip().lower() if h else f'col_{j}' for j, h in enumerate(row)]
            else:
                row_data = {}
                for j, value in enumerate(row):
                    if j < len(headers):
                        row_data[headers[j]] = value
                if any(v is not None for v in row_data.values()):
                    rows.append(row_data)

        workbook.close()
        return rows

    @staticmethod
    def import_metrics_data(rows, user=None):
        """Импортирует данные показателей из распарсенных строк"""
        imported = 0
        errors = []

        for i, row in enumerate(rows):
            try:
                metric_name = row.get('показатель') or row.get('metric_name') or row.get('name')
                if not metric_name:
                    errors.append(f'Строка {i+2}: не указан показатель')
                    continue

                metric_type, _ = MetricType.objects.get_or_create(
                    name=metric_name,
                    defaults={'unit': row.get('единица_измерения', ''), 'category': row.get('категория', '')}
                )

                date_value = row.get('дата') or row.get('date')
                if isinstance(date_value, str):
                    date_value = datetime.strptime(date_value, '%d.%m.%Y').date()
                elif isinstance(date_value, datetime):
                    date_value = date_value.date()
                else:
                    errors.append(f'Строка {i+2}: неверный формат даты')
                    continue

                MetricsData.objects.create(
                    metric_type=metric_type,
                    value=float(row.get('значение', 0)),
                    date=date_value,
                    district=row.get('район') or row.get('district', ''),
                    department=row.get('подразделение') or row.get('department', ''),
                    source='Excel import'
                )
                imported += 1

            except Exception as e:
                errors.append(f'Строка {i+2}: {str(e)}')

        return imported, errors

    @staticmethod
    def import_properties(rows, user=None):
        """Импортирует данные объектов недвижимости"""
        imported = 0
        errors = []

        for i, row in enumerate(rows):
            try:
                address = row.get('адрес') or row.get('address')
                if not address:
                    errors.append(f'Строка {i+2}: не указан адрес')
                    continue

                Property.objects.create(
                    address=address,
                    cadastral_number=row.get('кадастровый_номер') or row.get('cadastral_number', ''),
                    district=row.get('район') or row.get('district', ''),
                    property_type=row.get('тип_недвижимости') or row.get('property_type', 'жилое'),
                    total_area=float(row.get('площадь', 0)) if row.get('площадь') else None,
                    status=row.get('статус') or row.get('status', 'эксплуатируется'),
                    renovation_status=row.get('статус_реновации') or row.get('renovation_status', ''),
                    build_year=int(row.get('год_постройки')) if row.get('год_постройки') else None,
                    floors=int(row.get('этажность')) if row.get('этажность') else None,
                )
                imported += 1

            except Exception as e:
                errors.append(f'Строка {i+2}: {str(e)}')

        return imported, errors

    @staticmethod
    def import_hr_status(rows, user=None):
        data = []
        errors = []

        # ОТЛАДКА: печатаем первые 2 строки
        if rows:
            print("=" * 50)
            print("ПЕРВАЯ СТРОКА (ключи):", list(rows[0].keys()))
            print("ПЕРВАЯ СТРОКА (значения):", rows[0])
            if len(rows) > 1:
                print("ВТОРАЯ СТРОКА:", rows[1])
            print("=" * 50)

        for i, row in enumerate(rows):
            try:
                # Берём ВСЕ значения из строки по порядку
                values = list(row.values())

                fio = str(values[1]).strip() if len(values) > 1 else ''
                position = str(values[2]).strip() if len(values) > 2 else ''
                category = str(values[3]).strip() if len(values) > 3 else ''
                org = str(values[4]).strip() if len(values) > 4 else ''
                status = str(values[5]).strip() if len(values) > 5 else ''

                data.append({
                    'fio': fio,
                    'position': position,
                    'category': category,
                    'organization': org,
                    'status': status,
                })
            except Exception as e:
                errors.append(f'Строка {i + 2}: {str(e)}')

        # Агрегация
        summary = {}
        for item in data:
            full_org = item['organization'] or 'Не указано'
            org_parts = full_org.split(' / ')
            management = org_parts[0] if org_parts else full_org

            if management not in summary:
                summary[management] = {
                    'total': 0,
                    'specialists': 0,
                    'managers': 0,
                    'not_completed': 0,
                }

            summary[management]['total'] += 1

            cat = item['category'].lower()
            if 'руководитель' in cat:
                summary[management]['managers'] += 1
            else:
                summary[management]['specialists'] += 1

            if 'не пройдено' in item['status'].lower():
                summary[management]['not_completed'] += 1

        return data, summary, errors