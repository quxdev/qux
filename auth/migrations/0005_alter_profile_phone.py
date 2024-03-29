# Generated by Django 4.1.5 on 2023-05-03 10:49

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("qux_auth", "0004_servicemode_profile_is_live_alter_profile_company"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="phone",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=16,
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
                        regex="^\\+?[1-9]\\d{4,14}$",
                    )
                ],
            ),
        ),
    ]
