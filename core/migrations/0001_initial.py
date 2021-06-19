# Generated by Django 3.2 on 2021-06-19 14:14

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dtm_created', models.DateTimeField(auto_now_add=True, verbose_name='DTM Created')),
                ('dtm_updated', models.DateTimeField(auto_now=True, verbose_name='DTM Updated')),
                ('name', models.CharField(max_length=128)),
                ('address', models.TextField(blank=True, default=None, null=True)),
                ('domain', models.CharField(max_length=255)),
                ('url', models.URLField(blank=True, default=None, max_length=1024, null=True)),
            ],
            options={
                'verbose_name': 'Company',
                'verbose_name_plural': 'Companies',
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dtm_created', models.DateTimeField(auto_now_add=True, verbose_name='DTM Created')),
                ('dtm_updated', models.DateTimeField(auto_now=True, verbose_name='DTM Updated')),
                ('phone', models.CharField(max_length=16, validators=[django.core.validators.RegexValidator(message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.", regex='^\\+?[1-9]\\d{4,14}$')])),
                ('title', models.CharField(blank=True, default=None, max_length=255, null=True)),
                ('company', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='qux_core.company')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Profile',
            },
        ),
    ]
