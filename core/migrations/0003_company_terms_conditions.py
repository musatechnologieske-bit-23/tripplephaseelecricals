from django.db import migrations, models


TERMS = (
    "1. Goods once sold are not returnable and remain property of "
    "Tripple Phase Electricals Ltd until fully paid for.\n"
    "2. Our Official Bank Account details remain unchanged. Confirm any "
    "requested change through the company's Official channels."
)


def update_existing_company_terms(apps, schema_editor):
    company_settings = apps.get_model("core", "CompanySettings")
    company_settings.objects.using(schema_editor.connection.alias).filter(pk=1).update(
        terms=TERMS
    )


class Migration(migrations.Migration):
    dependencies = [("core", "0002_company_contact_details")]

    operations = [
        migrations.AlterField(
            model_name="companysettings",
            name="terms",
            field=models.TextField(default=TERMS),
        ),
        migrations.RunPython(update_existing_company_terms, migrations.RunPython.noop),
    ]