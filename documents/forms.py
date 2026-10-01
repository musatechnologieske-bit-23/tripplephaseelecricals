from django import forms
from django.forms import inlineformset_factory

from .models import Document, DocumentItem


class DocumentForm(forms.ModelForm):
    payment_terms = forms.ChoiceField(
        choices=Document.PaymentTerms.choices,
        required=False,
        initial=Document.PaymentTerms.CASH,
        widget=forms.RadioSelect(attrs={"class": "payment-term-choice"}),
    )

    class Meta:
        model = Document
        fields = (
            "doc_type",
            "issue_date",
            "valid_until",
            "due_date",
            "client_name",
            "client_phone",
            "client_email",
            "client_address",
            "client_pin",
            "notes",
            "payment_terms",
            "apply_vat",
        )
        widgets = {
            "doc_type": forms.Select(attrs={"class": "field-input"}),
            "issue_date": forms.DateInput(attrs={"type": "date", "class": "field-input"}),
            "valid_until": forms.DateInput(attrs={"type": "date", "class": "field-input"}),
            "due_date": forms.DateInput(attrs={"type": "date", "class": "field-input"}),
            "client_name": forms.TextInput(attrs={"class": "field-input", "autocomplete": "organization"}),
            "client_phone": forms.TextInput(attrs={"class": "field-input", "autocomplete": "tel"}),
            "client_email": forms.EmailInput(attrs={"class": "field-input", "autocomplete": "email"}),
            "client_address": forms.Textarea(attrs={"class": "field-input", "rows": 3}),
            "client_pin": forms.TextInput(attrs={"class": "field-input"}),
            "notes": forms.Textarea(attrs={"class": "field-input", "rows": 3}),
            "payment_terms": forms.RadioSelect(attrs={"class": "payment-term-choice"}),
            "apply_vat": forms.CheckboxInput(attrs={"class": "vat-toggle"}),
        }
        labels = {
            "doc_type": "Document type",
            "issue_date": "Issue date",
            "valid_until": "Valid until",
            "due_date": "Due date",
            "client_pin": "Client KRA PIN",
            "payment_terms": "Payment term",
            "apply_vat": "Apply VAT",
        }


class DocumentItemForm(forms.ModelForm):
    class Meta:
        model = DocumentItem
        fields = ("description", "quantity", "unit_price")
        widgets = {
            "description": forms.TextInput(attrs={"class": "item-input", "placeholder": "Description"}),
            "quantity": forms.NumberInput(attrs={"class": "item-input quantity-input", "min": "0.01", "step": "0.01"}),
            "unit_price": forms.NumberInput(attrs={"class": "item-input price-input", "min": "0", "step": "0.01"}),
        }


DocumentItemFormSet = inlineformset_factory(
    Document,
    DocumentItem,
    form=DocumentItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
