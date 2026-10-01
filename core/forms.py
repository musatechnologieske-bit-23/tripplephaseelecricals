from django import forms

from .models import CompanySettings


class CompanySettingsForm(forms.ModelForm):
    class Meta:
        model = CompanySettings
        fields = (
            "name",
            "logo",
            "address",
            "phone",
            "email",
            "kra_pin",
            "payment_details",
            "terms",
            "vat_rate",
        )
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "payment_details": forms.Textarea(attrs={"rows": 3}),
            "terms": forms.Textarea(attrs={"rows": 4}),
            "vat_rate": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }
