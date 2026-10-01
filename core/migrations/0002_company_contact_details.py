from django.db import migrations, models


COMPANY_DETAILS = {
    "name": "Tripple Phase Electricals Limited",
    "address": "CHARLES RUBIA LANE\nNAIROBI 586635-00100\nKenya",
    "phone": "0748645468",
    "email": "info@tripplephaseelectricals.com",
    "kra_pin": "P051777360U",
    "payment_details": "Tripple Phase Electricals Limited\nEquity Bank\n0940278884568",
}


def update_existing_company_settings(apps, schema_editor):
    company_settings = apps.get_model("core", "CompanySettings")
    company_settings.objects.using(schema_editor.connection.alias).filter(pk=1).update(
        **COMPANY_DETAILS
    )


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="companysettings",
            name="name",
            field=models.CharField(default="Tripple Phase Electricals Limited", max_length=160),
        ),
        migrations.AlterField(
            model_name="companysettings",
            name="address",
            field=models.TextField(default="CHARLES RUBIA LANE\nNAIROBI 586635-00100\nKenya"),
        ),
        migrations.AlterField(
            model_name="companysettings",
            name="phone",
            field=models.CharField(default="0748645468", max_length=40),
        ),
        migrations.AlterField(
            model_name="companysettings",
            name="email",
            field=models.EmailField(
                blank=True, default="info@tripplephaseelectricals.com", max_length=254
            ),
        ),
        migrations.AlterField(
            model_name="companysettings",
            name="payment_details",
            field=models.TextField(
                default="Tripple Phase Electricals Limited\nEquity Bank\n0940278884568"
            ),
        ),
        migrations.RunPython(update_existing_company_settings, migrations.RunPython.noop),
    ]