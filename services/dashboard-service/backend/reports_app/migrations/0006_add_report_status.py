# Generated migration for adding status field to Report

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reports_app', '0004_sync_comment_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='status',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True,
                related_name='reports',
                to='reports_app.reportstatus'
            ),
        ),
    ]
