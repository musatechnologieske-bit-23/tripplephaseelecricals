from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.template.loader import render_to_string
from django.urls import reverse
from weasyprint import HTML

from core.models import CompanySettings

from .models import Document, DocumentItem, DocumentType
from .views import _print_context


class DocumentModelTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.user = get_user_model().objects.create_user(username="staff", password="test-password")

	def setUp(self):
		self.client.force_login(self.user)

	def make_document(self, doc_type=DocumentType.QUOTATION, **kwargs):
		return Document.objects.create(
			doc_type=doc_type,
			client_name="Example Client",
			created_by=self.user,
			**kwargs,
		)

	def test_number_sequences_are_independent(self):
		quotation = self.make_document()
		invoice = self.make_document(DocumentType.INVOICE)
		next_quotation = self.make_document()

		self.assertEqual(quotation.number, "QT-0001")
		self.assertEqual(invoice.number, "INV-0001")
		self.assertEqual(next_quotation.number, "QT-0002")
		self.assertEqual(invoice.status, Document.Status.UNPAID)

	def test_vat_example_and_half_up_rounding(self):
		quotation = self.make_document()
		DocumentItem.objects.create(
			document=quotation,
			description="Electrical installation",
			quantity=Decimal("1139000.00"),
			unit_price=Decimal("1.00"),
		)
		quotation.recalculate_totals()

		self.assertEqual(quotation.subtotal, Decimal("1139000.00"))
		self.assertEqual(quotation.vat_amount, Decimal("182240.00"))
		self.assertEqual(quotation.total, Decimal("1321240.00"))

		settings = CompanySettings.load()
		settings.vat_rate = Decimal("10.00")
		settings.save()
		rounded = self.make_document()
		DocumentItem.objects.create(
			document=rounded,
			description="Rounding check",
			quantity=Decimal("1.00"),
			unit_price=Decimal("0.05"),
		)
		rounded.recalculate_totals()
		self.assertEqual(rounded.vat_amount, Decimal("0.01"))

	def test_vat_can_be_disabled(self):
		quotation = self.make_document(apply_vat=False)
		DocumentItem.objects.create(
			document=quotation,
			description="Cable",
			quantity=Decimal("2.00"),
			unit_price=Decimal("100.00"),
		)
		quotation.recalculate_totals()

		self.assertEqual(quotation.vat_amount, Decimal("0.00"))
		self.assertEqual(quotation.total, Decimal("200.00"))

	def test_payment_terms_are_stored_for_quotation(self):
		quotation = self.make_document(payment_terms=Document.PaymentTerms.CREDIT)

		self.assertEqual(quotation.payment_terms, Document.PaymentTerms.CREDIT)

	def test_duplicate_document_copies_items_and_creates_new_number(self):
		quotation = self.make_document(doc_type=DocumentType.QUOTATION)
		DocumentItem.objects.create(
			document=quotation,
			description="Cable",
			quantity=Decimal("2.00"),
			unit_price=Decimal("100.00"),
		)
		quotation.recalculate_totals()

		response = self.client.post(reverse("documents:duplicate", args=(quotation.pk,)))

		self.assertRedirects(response, reverse("documents:edit", args=(Document.objects.latest("pk").pk,)))
		duplicate = Document.objects.order_by("-pk").first()
		self.assertNotEqual(duplicate.pk, quotation.pk)
		self.assertEqual(duplicate.number, "QT-0002")
		self.assertEqual(duplicate.client_name, quotation.client_name)
		self.assertEqual(duplicate.items.count(), 1)
		self.assertEqual(duplicate.items.first().description, "Cable")

	def test_convert_quotation_to_invoice_links_original_document(self):
		quotation = self.make_document(doc_type=DocumentType.QUOTATION)
		DocumentItem.objects.create(
			document=quotation,
			description="Lighting circuit",
			quantity=Decimal("3.00"),
			unit_price=Decimal("250.00"),
		)
		quotation.recalculate_totals()

		response = self.client.post(reverse("documents:convert", args=(quotation.pk,)))

		self.assertRedirects(response, reverse("documents:print", args=(Document.objects.exclude(pk=quotation.pk).get().pk,)))
		quotation.refresh_from_db()
		converted = quotation.conversions.get()
		self.assertEqual(converted.doc_type, DocumentType.INVOICE)
		self.assertEqual(converted.status, Document.Status.UNPAID)
		self.assertEqual(converted.converted_from, quotation)
		self.assertEqual(quotation.status, Document.Status.CONVERTED)

	def test_mark_invoice_paid_records_payment(self):
		invoice = self.make_document(doc_type=DocumentType.INVOICE)
		invoice.status = Document.Status.UNPAID
		invoice.save(update_fields=["status"])

		response = self.client.post(
			reverse("documents:mark-paid", args=(invoice.pk,)),
			{"paid_date": "2026-09-29", "payment_method": "mpesa"},
		)

		self.assertRedirects(response, reverse("documents:print", args=(invoice.pk,)))
		invoice.refresh_from_db()
		self.assertEqual(invoice.status, Document.Status.PAID)
		self.assertEqual(invoice.paid_date.isoformat(), "2026-09-29")
		self.assertEqual(invoice.payment_method, Document.PaymentMethod.MPESA)

	def test_existing_quotation_can_be_edited(self):
		quotation = self.make_document(status=Document.Status.SENT)
		item = DocumentItem.objects.create(
			document=quotation,
			description="Cable",
			quantity=Decimal("2.00"),
			unit_price=Decimal("100.00"),
		)
		original_number = quotation.number

		response = self.client.post(
			reverse("documents:edit", args=(quotation.pk,)),
			{
				"issue_date": quotation.issue_date.isoformat(),
				"valid_until": "",
				"due_date": "",
				"client_name": "Updated Client",
				"client_phone": "",
				"client_email": "",
				"client_address": "",
				"client_pin": "",
				"notes": "",
				"payment_terms": "cash",
				"apply_vat": "on",
				"items-TOTAL_FORMS": "2",
				"items-INITIAL_FORMS": "1",
				"items-MIN_NUM_FORMS": "1",
				"items-MAX_NUM_FORMS": "1000",
				"items-0-id": str(item.pk),
				"items-0-description": "Installed cable",
				"items-0-quantity": "3.00",
				"items-0-unit_price": "150.00",
				"items-1-id": "",
				"items-1-description": "",
				"items-1-quantity": "",
				"items-1-unit_price": "",
			},
		)

		self.assertRedirects(response, reverse("documents:list"))
		quotation.refresh_from_db()
		self.assertEqual(quotation.number, original_number)
		self.assertEqual(quotation.status, Document.Status.SENT)
		self.assertEqual(quotation.client_name, "Updated Client")
		self.assertEqual(quotation.items.get().description, "Installed cable")
		self.assertEqual(quotation.total, Decimal("522.00"))


class DocumentFormTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(username="staff", password="test-password")
		self.client.force_login(self.user)

	def test_create_form_saves_document_and_items(self):
		response = self.client.post(
			reverse("documents:create"),
			{
				"doc_type": "quotation",
				"issue_date": "2026-09-28",
				"valid_until": "",
				"due_date": "",
				"client_name": "Example Client",
				"client_phone": "",
				"client_email": "",
				"client_address": "",
				"client_pin": "",
				"notes": "",
				"apply_vat": "on",
				"items-TOTAL_FORMS": "1",
				"items-INITIAL_FORMS": "0",
				"items-MIN_NUM_FORMS": "1",
				"items-MAX_NUM_FORMS": "1000",
				"items-0-description": "Cable",
				"items-0-quantity": "2.00",
				"items-0-unit_price": "1000.00",
				"items-0-id": "",
			},
		)

		self.assertRedirects(response, reverse("documents:list"))
		document = Document.objects.get()
		self.assertEqual(document.number, "QT-0001")
		self.assertEqual(document.created_by, self.user)
		self.assertEqual(document.subtotal, Decimal("2000.00"))
		self.assertEqual(document.vat_amount, Decimal("320.00"))
		self.assertEqual(document.total, Decimal("2320.00"))
		self.assertEqual(document.items.count(), 1)

	def test_document_pages_require_login(self):
		self.client.logout()

		response = self.client.get(reverse("documents:list"))

		self.assertRedirects(response, f"{reverse('login')}?next={reverse('documents:list')}")


class DocumentRegisterTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(username="register-user", password="test-password")
		self.client.force_login(self.user)

	def test_sales_register_contains_only_paid_invoices(self):
		paid_invoice = Document.objects.create(
			doc_type=DocumentType.INVOICE,
			client_name="Paid Client",
			created_by=self.user,
			status=Document.Status.PAID,
		)
		Document.objects.create(
			doc_type=DocumentType.INVOICE,
			client_name="Unpaid Client",
			created_by=self.user,
		)
		Document.objects.create(
			doc_type=DocumentType.QUOTATION,
			client_name="Quoted Client",
			created_by=self.user,
		)

		response = self.client.get(reverse("documents:list"), {"type": "sales"})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, paid_invoice.number)
		self.assertContains(response, "Paid Client")
		self.assertNotContains(response, "Unpaid Client")
		self.assertNotContains(response, "Quoted Client")

	def test_register_search_and_pagination(self):
		for index in range(21):
			Document.objects.create(
				doc_type=DocumentType.QUOTATION,
				client_name=f"Client {index:02d}",
				created_by=self.user,
			)

		first_page = self.client.get(reverse("documents:list"), {"type": "quotation"})
		search_result = self.client.get(
			reverse("documents:list"), {"type": "quotation", "q": "Client 20"}
		)

		self.assertEqual(first_page.context["page_obj"].paginator.count, 21)
		self.assertTrue(first_page.context["page_obj"].has_next())
		self.assertEqual(search_result.context["page_obj"].paginator.count, 1)
		self.assertContains(search_result, "Client 20")


class DocumentPrintTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(username="printer", password="test-password")
		self.client.force_login(self.user)
		self.document = Document.objects.create(
			doc_type=DocumentType.INVOICE,
			client_name="Example Client",
			created_by=self.user,
		)
		for description in ("Supply and installation", "Electrical materials"):
			DocumentItem.objects.create(
				document=self.document,
				description=description,
				quantity=Decimal("1.00"),
				unit_price=Decimal("1000.00"),
			)
		self.document.recalculate_totals()

	def render_pdf_pages(self):
		context = {**_print_context(self.document), "pdf_mode": True}
		markup = render_to_string("documents/print.html", context)
		return HTML(string=markup, base_url="http://testserver/").render().pages

	def test_print_view_shows_document_and_print_action(self):
		response = self.client.get(reverse("documents:print", args=(self.document.pk,)))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.document.number)
		self.assertContains(response, "window.print()")
		self.assertContains(response, "Banking Details")
		self.assertContains(response, "Terms & Conditions")
		self.assertContains(response, "Goods once sold are not returnable")
		self.assertContains(response, "Official Bank Account details remain unchanged")
		self.assertContains(response, "data:image/png;base64")
		self.assertContains(response, "Banking Details")
		self.assertContains(response, "Payable To")
		self.assertContains(response, "Jacinta")

	def test_pdf_download_returns_valid_pdf(self):
		response = self.client.get(reverse("documents:pdf", args=(self.document.pk,)))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response["Content-Type"], "application/pdf")
		self.assertIn("attachment; filename=", response["Content-Disposition"])
		self.assertTrue(response.content.startswith(b"%PDF-"))

	def test_typical_document_fits_one_page(self):
		self.assertEqual(len(self.render_pdf_pages()), 1)

	def test_long_document_paginates(self):
		for item_number in range(90):
			DocumentItem.objects.create(
				document=self.document,
				description=f"Electrical supply and installation item {item_number:03d}",
				quantity=Decimal("2.00"),
				unit_price=Decimal("1250.00"),
			)
		self.document.recalculate_totals()

		page_count = len(self.render_pdf_pages())

		self.assertGreater(page_count, 1)
		self.assertLessEqual(page_count, 4)
