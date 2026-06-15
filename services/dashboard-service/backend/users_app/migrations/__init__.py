from django.db import migrations

def load_initial_data(apps, schema_editor):
    Role = apps.get_model('users_app', 'Role')
    Role.objects.create(name='Admin', description='Полный доступ')
    Role.objects.create(name='Manager', description='Управление отчетами')
    Role.objects.create(name='Analyst', description='Аналитика')
    Role.objects.create(name='Viewer', description='Просмотр')

class Migration(migrations.Migration):
    dependencies = [
        ('users_app', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(load_initial_data),
    ]