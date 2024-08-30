# Generated by Django 5.1 on 2024-08-28 07:18

import chat.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text_content', models.TextField(blank=True, null=True)),
                ('audio_content', models.FileField(blank=True, null=True, upload_to='audio/', validators=[chat.models.validate_audio_file, chat.models.validate_file_size])),
                ('file_content', models.FileField(blank=True, null=True, upload_to='files/', validators=[chat.models.validate_file_type, chat.models.validate_file_size])),
                ('date_sent', models.DateTimeField(auto_now_add=True)),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['date_sent'],
            },
        ),
    ]
