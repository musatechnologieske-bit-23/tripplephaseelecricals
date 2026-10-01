from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone


CENT = Decimal("0.01")


class DocumentType(models.TextChoices):
	QUOTATION = "quotation", "Quotation"
	INVOICE = "invoice", "Invoice"


class DocumentNumberSequence(models.Model):
	doc_type = models.CharField(max_length=12, choices=DocumentType.choices, unique=True)
	last_number = models.PositiveIntegerField(default=0)

	def __str__(self):
		return f"{self.doc_type}: {self.last_number}"


class Document(models.Model):
	class Status(models.TextChoices):
		DRAFT = "draft", "Draft"
		SENT = "sent", "Sent"
		ACCEPTED = "accepted", "Accepted"
		CONVERTED = "converted", "Converted"
		UNPAID = "unpaid", "Unpaid"
		PAID = "paid", "Paid"
		CANCELLED = "cancelled", "Cancelled"

	class PaymentTerms(models.TextChoices):
		CASH = "cash", "Cash"
		CREDIT = "credit", "Credit"
		APPROVED = "approved", "Approved"

	class PaymentMethod(models.TextChoices):
		CASH = "cash", "Cash"
		MPESA = "mpesa", "M-Pesa"
		BANK = "bank", "Bank"
		CHEQUE = "cheque", "Cheque"

	doc_type = models.CharField(max_length=12, choices=DocumentType.choices)
	number = models.CharField(max_length=16, unique=True, blank=True)
	issue_date = models.DateField(default=timezone.localdate)
	valid_until = models.DateField(null=True, blank=True)
	due_date = models.DateField(null=True, blank=True)
	client_name = models.CharField(max_length=160)
	client_phone = models.CharField(max_length=40, blank=True)
	client_email = models.EmailField(blank=True)
	client_address = models.TextField(blank=True)
	client_pin = models.CharField(max_length=20, blank=True)
	notes = models.TextField(blank=True)
	payment_terms = models.CharField(
		max_length=12,
		choices=PaymentTerms.choices,
		default=PaymentTerms.CASH,
	)
	apply_vat = models.BooleanField(default=True)
	subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
	vat_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
	total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
	status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
	paid_date = models.DateField(null=True, blank=True)
	payment_method = models.CharField(max_length=12, choices=PaymentMethod.choices, blank=True)
	converted_from = models.ForeignKey(
		"self", null=True, blank=True, on_delete=models.SET_NULL, related_name="conversions"
	)
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="documents"
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ("-issue_date", "-id")
		indexes = [
			models.Index(fields=("doc_type", "issue_date"), name="doc_type_issue_idx"),
			models.Index(fields=("status", "issue_date"), name="doc_status_issue_idx"),
		]

	def __str__(self):
		return self.number or self.get_doc_type_display()

	def save(self, *args, **kwargs):
		if self._state.adding and not self.number:
			prefix = "QT" if self.doc_type == DocumentType.QUOTATION else "INV"
			initial_status = (
				self.Status.DRAFT
				if self.doc_type == DocumentType.QUOTATION
				else self.Status.UNPAID
			)
			if self.status == self.Status.DRAFT:
				self.status = initial_status

			with transaction.atomic():
				sequence, _ = DocumentNumberSequence.objects.get_or_create(doc_type=self.doc_type)
				sequence.last_number += 1
				sequence.save(update_fields=("last_number",))
				self.number = f"{prefix}-{sequence.last_number:04d}"
				super().save(*args, **kwargs)
			return
		super().save(*args, **kwargs)

	def clean(self):
		if (
			self._state.adding
			and self.doc_type == DocumentType.INVOICE
			and self.status == self.Status.DRAFT
		):
			self.status = self.Status.UNPAID

		quotation_statuses = {
			self.Status.DRAFT,
			self.Status.SENT,
			self.Status.ACCEPTED,
			self.Status.CONVERTED,
		}
		invoice_statuses = {self.Status.UNPAID, self.Status.PAID, self.Status.CANCELLED}
		allowed_statuses = (
			quotation_statuses if self.doc_type == DocumentType.QUOTATION else invoice_statuses
		)
		if self.status not in allowed_statuses:
			from django.core.exceptions import ValidationError

			raise ValidationError({"status": "Choose a status that matches the document type."})

	def recalculate_totals(self, save=True):
		from core.models import CompanySettings

		self.subtotal = sum((item.line_total for item in self.items.all()), Decimal("0.00"))
		if self.apply_vat:
			vat_rate = CompanySettings.load().vat_rate
			self.vat_amount = (self.subtotal * vat_rate / Decimal("100")).quantize(
				CENT, rounding=ROUND_HALF_UP
			)
		else:
			self.vat_amount = Decimal("0.00")
		self.total = self.subtotal + self.vat_amount
		if save:
			self.save(update_fields=("subtotal", "vat_amount", "total"))
		return self.subtotal, self.vat_amount, self.total


class DocumentItem(models.Model):
	document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="items")
	description = models.CharField(max_length=240)
	quantity = models.DecimalField(
		max_digits=10,
		decimal_places=2,
		validators=[MinValueValidator(Decimal("0.01"))],
	)
	unit_price = models.DecimalField(
		max_digits=12,
		decimal_places=2,
		validators=[MinValueValidator(Decimal("0.00"))],
	)
	line_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

	class Meta:
		ordering = ("id",)

	def save(self, *args, **kwargs):
		self.line_total = (self.quantity * self.unit_price).quantize(CENT, rounding=ROUND_HALF_UP)
		super().save(*args, **kwargs)

	def __str__(self):
		return self.description
from django.db import models

# Create your models here.
