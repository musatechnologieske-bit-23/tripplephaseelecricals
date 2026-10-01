from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from documents.models import Document, DocumentItem, DocumentType

from .models import CompanySettings


class PhaseOneAccessTests(TestCase):
    def test_home_requires_login(self):
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('home')}")

    def test_staff_cannot_edit_company_settings(self):
        staff = get_user_model().objects.create_user(username="staff", password="test-password")
        self.client.force_login(staff)

        response = self.client.get(reverse("company-settings"))

        self.assertEqual(response.status_code, 403)

    def test_superuser_can_edit_company_settings(self):
        superuser = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="test-password"
        )
        self.client.force_login(superuser)

        response = self.client.post(
            reverse("company-settings"),
            {
                "name": "Tripple Phase Electricals Ltd",
                "address": "Nairobi",
                "phone": "0700000000",
                "email": "",
                "kra_pin": "P051777360U",
                "payment_details": "Bank details",
                "terms": "Payment due on receipt",
                "vat_rate": "16.00",
            },
        )

        self.assertRedirects(response, reverse("company-settings"))
        self.assertEqual(CompanySettings.load().name, "Tripple Phase Electricals Ltd")

    def test_company_settings_default_to_supplied_contact_and_bank_details(self):
        company = CompanySettings.load()

        self.assertEqual(company.name, "Tripple Phase Electricals Limited")
        self.assertEqual(company.address, "CHARLES RUBIA LANE\nNAIROBI 586635-00100\nKenya")
        self.assertEqual(company.phone, "0748645468")
        self.assertEqual(company.email, "info@tripplephaseelectricals.com")
        self.assertEqual(company.kra_pin, "P051777360U")
        self.assertIn("Equity Bank", company.payment_details)
        self.assertIn("0940278884568", company.payment_details)
        self.assertIn("Goods once sold are not returnable", company.terms)
        self.assertIn("Official Bank Account details remain unchanged", company.terms)


class DashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="dashboard-user", password="test-password")
        self.client.force_login(self.user)

    def test_dashboard_shows_current_month_stats_only(self):
        today = timezone.localdate()
        quotation = Document.objects.create(
            doc_type=DocumentType.QUOTATION,
            issue_date=today,
            client_name="Quote Client",
            created_by=self.user,
        )
        DocumentItem.objects.create(
            document=quotation,
            description="Quote item",
            quantity=Decimal("2.00"),
            unit_price=Decimal("100.00"),
        )
        quotation.recalculate_totals()

        invoice = Document.objects.create(
            doc_type=DocumentType.INVOICE,
            issue_date=today,
            client_name="Invoice Client",
            created_by=self.user,
            status=Document.Status.PAID,
            paid_date=today,
            payment_method=Document.PaymentMethod.MPESA,
        )
        DocumentItem.objects.create(
            document=invoice,
            description="Invoice item",
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
        )
        invoice.recalculate_totals()

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stats"]["quoted_total"], Decimal("232.00"))
        self.assertEqual(response.context["stats"]["invoiced_total"], Decimal("116.00"))
        self.assertEqual(response.context["stats"]["paid_total"], Decimal("116.00"))
        self.assertEqual(response.context["stats"]["outstanding_total"], Decimal("0.00"))
        self.assertEqual(response.context["stats"]["vat_total"], Decimal("16.00"))
        self.assertContains(response, "Current month statistics")
        self.assertNotContains(response, "Recent activity")
        self.assertNotContains(response, "Quote Client")
        self.assertNotContains(response, "Invoice Client")
