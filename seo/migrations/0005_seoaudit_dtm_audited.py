from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("qux_seo", "0004_seo_audit_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="seoaudit",
            name="dtm_audited",
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
    ]
