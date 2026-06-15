from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.http import FileResponse
from django.utils import timezone
import os
import tempfile

from .models import ReportStatus, ReportTemplate, Report, SharedReport, Comment, ExcelImportQueue
from .serializers import (
    ReportStatusSerializer,
    ReportTemplateSerializer,
    ReportSerializer,
    SharedReportSerializer,
    CommentSerializer,
    ExcelImportQueueSerializer,
)
from .services import PPTXGenerator
from .excel_service import ExcelImporter


# ===========================
# СТАТУСЫ ОТЧЁТОВ
# ===========================
class ReportStatusViewSet(viewsets.ModelViewSet):
    queryset = ReportStatus.objects.all()
    serializer_class = ReportStatusSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        # Автоматически создаем статусы если их нет
        if ReportStatus.objects.count() == 0:
            default_statuses = [
                {'name': 'Черновик', 'description': 'Отчёт в черновике'},
                {'name': 'На согласовании', 'description': 'Отчёт на согласовании'},
                {'name': 'Согласован', 'description': 'Отчёт согласован'},
                {'name': 'Отклонён', 'description': 'Отчёт отклонён'},
                {'name': 'Опубликован', 'description': 'Отчёт опубликован'},
            ]
            for status_data in default_statuses:
                ReportStatus.objects.create(**status_data)
        return super().list(request, *args, **kwargs)


# ===========================
# ШАБЛОНЫ ОТЧЁТОВ
# ===========================
class ReportTemplateViewSet(viewsets.ModelViewSet):
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def public(self, request):
        public_templates = self.get_queryset().filter(is_public=True)
        serializer = self.get_serializer(public_templates, many=True)
        return Response(serializer.data)


# ===========================
# ОТЧЁТЫ
# ===========================
class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Report.objects.all()
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset

    def destroy(self, request, *args, **kwargs):
        """Удаляет отчет (Django сам обработает каскадное удаление через ForeignKey)"""
        report = self.get_object()
        report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def generate_pptx(self, request, pk=None):
        report = self.get_object()

        try:
            from .services import PPTXGenerator
            generator = PPTXGenerator(report)
            pptx_path = generator.generate()

            report.file_path = pptx_path
            report.save()

            response = FileResponse(
                open(pptx_path, 'rb'),
                content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation'
            )
            response['Content-Disposition'] = f'attachment; filename="report_{report.id}.pptx"'
            return response

        except Exception as e:
            return Response(
                {'error': f'Ошибка генерации PPTX: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def generate_pdf(self, request, pk=None):
        """Генерирует PDF-файл из отчёта"""
        report = self.get_object()

        try:
            from .pdf_service import PDFGenerator
            generator = PDFGenerator(report)
            pdf_path = generator.generate()

            report.file_path = pdf_path
            report.save()

            response = FileResponse(
                open(pdf_path, 'rb'),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="report_{report.id}.pdf"'
            return response

        except Exception as e:
            return Response(
                {'error': f'Ошибка генерации PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def update_data(self, request, pk=None):
        """Обновляет данные отчёта из импортированных данных"""
        report = self.get_object()
        data = request.data.get('data', {})

        report.data = data
        report.save()

        serializer = self.get_serializer(report)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def load_from_metrics(self, request, pk=None):
        """Загружает данные из MetricsData в отчёт и создаёт структуру слайдов"""
        report = self.get_object()
        
        try:
            from dashboard_app.models import MetricsData, MetricType
            
            # Получаем все данные метрик
            metrics_data = MetricsData.objects.all()
            
            # Группируем данные по типу метрики и району
            metrics_by_type = {}
            for metric in metrics_data:
                metric_name = metric.metric_type.name
                if metric_name not in metrics_by_type:
                    metrics_by_type[metric_name] = []
                
                metrics_by_type[metric_name].append({
                    'value': float(metric.value),
                    'date': metric.date.isoformat() if metric.date else None,
                    'district': metric.district,
                    'department': metric.department,
                    'unit': metric.metric_type.unit,
                    'category': metric.metric_type.category
                })
            
            # Создаём структуру слайдов для PPTXGenerator
            slides = []
            
            # Титульный слайд
            slides.append({
                'layout': 'title',
                'elements': [
                    {'type': 'title', 'content': report.title},
                    {'type': 'subtitle', 'content': 'Департамент городского имущества города Москвы'},
                    {'type': 'date', 'content': report.created_at.strftime('%d.%m.%Y') if report.created_at else ''}
                ]
            })
            
            # Группируем метрики по категориям
            categories = {}
            for metric_name, data_list in metrics_by_type.items():
                category = data_list[0]['category'] if data_list else 'Прочее'
                if category not in categories:
                    categories[category] = []
                categories[category].append({'name': metric_name, 'data': data_list})
            
            # Слайды для каждой категории
            for category, metrics in categories.items():
                # Группируем все метрики категории по районам
                districts = {}
                for metric in metrics:
                    for item in metric['data']:
                        district = item['district'] or 'Не указан'
                        if district not in districts:
                            districts[district] = 0
                        districts[district] += item['value']
                
                slides.append({
                    'layout': 'content',
                    'heading': category,
                    'elements': [
                        {
                            'type': 'chart',
                            'chart_type': 'bar',
                            'title': category,
                            'data': {
                                'categories': list(districts.keys()),
                                'values': list(districts.values())
                            }
                        }
                    ]
                })
            
            report.data = {'slides': slides}
            report.save()
            
            print(f"Загружено {len(slides)} слайдов в отчет {report.id}")
            print(f"Данные отчета: {report.data}")
            
            serializer = self.get_serializer(report)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Ошибка загрузки данных: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Изменяет статус отчёта"""
        report = self.get_object()
        status_id = request.data.get('status_id')

        try:
            from .models import ReportStatus
            status = ReportStatus.objects.get(id=status_id)
            report.status = status
            report.save()

            serializer = self.get_serializer(report)
            return Response(serializer.data)
        except ReportStatus.DoesNotExist:
            return Response(
                {'error': 'Статус не найден'},
                status=status.HTTP_400_BAD_REQUEST
            )



# ===========================
# ОБЩИЕ ДОСТУПЫ
# ===========================
class SharedReportViewSet(viewsets.ModelViewSet):
    queryset = SharedReport.objects.all()
    serializer_class = SharedReportSerializer
    permission_classes = [permissions.IsAuthenticated]


# ===========================
# КОММЕНТАРИИ
# ===========================
class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]


# ===========================
# ИМПОРТ EXCEL
# ===========================
class ExcelImportViewSet(viewsets.ModelViewSet):
    queryset = ExcelImportQueue.objects.all()
    serializer_class = ExcelImportQueueSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload(self, request):
        file = request.FILES.get('file')
        import_type = request.data.get('import_type', 'metrics')

        if not file:
            return Response({'error': 'Файл не предоставлен'}, status=400)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            for chunk in file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        queue_item = ExcelImportQueue.objects.create(
            filename=file.name,
            status='processing'
        )

        try:
            rows = ExcelImporter.parse_file(tmp_path)

            if import_type == 'metrics':
                imported, errors = ExcelImporter.import_metrics_data(rows)
            elif import_type == 'properties':
                imported, errors = ExcelImporter.import_properties(rows)
            else:
                imported, errors = 0, ['Неизвестный тип импорта']

            queue_item.status = 'completed' if not errors else 'completed_with_errors'
            queue_item.raw_data = {'imported': imported, 'total_rows': len(rows), 'errors': errors}
            queue_item.processed_at = timezone.now()
            queue_item.save()

            return Response({
                'success': True,
                'imported': imported,
                'total_rows': len(rows),
                'errors': errors,
                'status': queue_item.status,
            })

        except Exception as e:
            queue_item.status = 'error'
            queue_item.error_message = str(e)
            queue_item.save()

            return Response({'success': False, 'error': str(e)}, status=500)

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @action(detail=False, methods=['get'])
    def history(self, request):
        history = ExcelImportQueue.objects.all().order_by('-created_at')[:20]
        serializer = self.get_serializer(history, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def hr_status(self, request):
        """Загружает Excel с HR-статусами и возвращает сводку"""
        file = request.FILES.get('file')

        if not file:
            return Response({'error': 'Файл не предоставлен'}, status=400)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            for chunk in file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            rows = ExcelImporter.parse_file(tmp_path)
            data, summary, errors = ExcelImporter.import_hr_status(rows)

            return Response({
                'success': True,
                'total_employees': len(data),
                'summary': summary,
                'errors': errors,
            })
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=500)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


