from decimal import Decimal

from django.db import models


class CompanySettings(models.Model):
    name = models.CharField(max_length=160, default="Tripple Phase Electricals Limited")
    logo = models.FileField(upload_to="company/", blank=True)
    address = models.TextField(default="CHARLES RUBIA LANE\nNAIROBI 586635-00100\nKenya")
    phone = models.CharField(max_length=40, default="0748645468")
    email = models.EmailField(blank=True, default="info@tripplephaseelectricals.com")
    kra_pin = models.CharField(max_length=20, default="P051777360U")
    payment_details = models.TextField(
        default="Tripple Phase Electricals Limited\nEquity Bank\n0940278884568"
    )
    terms = models.TextField(
        default=(
            "1. Goods once sold are not returnable and remain property of "
            "Tripple Phase Electricals Ltd until fully paid for.\n"
            "2. Our Official Bank Account details remain unchanged. Confirm any "
            "requested change through the company's Official channels."
        )
    )
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("16.00"))

    class Meta:
        verbose_name = "company settings"
        verbose_name_plural = "company settings"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
