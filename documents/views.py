import base64
import mimetypes
from datetime import timedelta
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from weasyprint import HTML

from core.models import CompanySettings

from .forms import DocumentForm, DocumentItemFormSet
from .models import Document, DocumentItem, DocumentType


def _logo_data_uri():
	logo_path = Path(settings.BASE_DIR) / "static" / "img" / "tripplephase-wordmark.png"
	logo_bytes = logo_path.read_bytes()
	content_type = mimetypes.guess_type(logo_path.name)[0] or "image/png"
	encoded_logo = base64.b64encode(logo_bytes).decode("ascii")
	return f"data:{content_type};base64,{encoded_logo}"


def _print_context(document):
	company = CompanySettings.load()
	return {
		"document": document,
		"company": company,
		"logo_data_uri": _logo_data_uri(),
	}


@login_required
def document_list(request):
	selected_type = request.GET.get("type", "all")
	documents = Document.objects.select_related("created_by")
	if selected_type == "quotation":
		documents = documents.filter(doc_type=DocumentType.QUOTATION)
	elif selected_type == "invoice":
		documents = documents.filter(doc_type=DocumentType.INVOICE)
	elif selected_type == "sales":
		documents = documents.filter(doc_type=DocumentType.INVOICE, status=Document.Status.PAID)
	else:
		selected_type = "all"

	search = request.GET.get("q", "").strip()
	if search:
		documents = documents.filter(Q(number__icontains=search) | Q(client_name__icontains=search))

	status = request.GET.get("status", "")
	if status in Document.Status.values:
		documents = documents.filter(status=status)
	else:
		status = ""

	date_from = parse_date(request.GET.get("date_from", ""))
	date_to = parse_date(request.GET.get("date_to", ""))
	if date_from:
		documents = documents.filter(issue_date__gte=date_from)
	if date_to:
		documents = documents.filter(issue_date__lte=date_to)

	page_obj = Paginator(documents, 20).get_page(request.GET.get("page"))
	query_params = request.GET.copy()
	query_params.pop("page", None)
	return render(
		request,
		"documents/list.html",
		{
			"page_obj": page_obj,
			"documents": page_obj.object_list,
			"selected_type": selected_type,
			"search": search,
			"selected_status": status,
			"status_choices": Document.Status.choices,
			"date_from": date_from.isoformat() if date_from else "",
			"date_to": date_to.isoformat() if date_to else "",
			"query_params": query_params.urlencode(),
		},
	)


@login_required
def document_form(request, pk=None):
	document = get_object_or_404(Document, pk=pk) if pk is not None else None
	initial_type = request.GET.get("type", "")
	if document is None and initial_type in {DocumentType.QUOTATION, DocumentType.INVOICE}:
		form = DocumentForm(request.POST or None, instance=document, initial={"doc_type": initial_type})
	else:
		form = DocumentForm(request.POST or None, instance=document)
	if document is not None:
		form.fields["doc_type"].disabled = True
	item_formset = DocumentItemFormSet(request.POST or None, instance=document)

	if request.method == "POST" and form.is_valid() and item_formset.is_valid():
		with transaction.atomic():
			saved_document = form.save(commit=False)
			if saved_document.pk is None:
				saved_document.created_by = request.user
			if not saved_document.payment_terms:
				saved_document.payment_terms = Document.PaymentTerms.CASH
			saved_document.save()
			item_formset.instance = saved_document
			item_formset.save()
			saved_document.recalculate_totals()
		messages.success(request, f"{saved_document.number} saved.")
		return redirect("documents:list")

	company = CompanySettings.load()
	return render(
		request,
		"documents/form.html",
		{
			"form": form,
			"item_formset": item_formset,
			"company": company,
			"document": document,
		},
	)


@login_required
def document_print(request, pk):
	document = get_object_or_404(Document.objects.prefetch_related("items"), pk=pk)
	context = _print_context(document)
	return render(request, "documents/print.html", {**context, "pdf_mode": False})


@login_required
def document_duplicate(request, pk):
	source = get_object_or_404(Document.objects.prefetch_related("items"), pk=pk)
	if request.method != "POST":
		return redirect("documents:edit", pk=source.pk)

	duplicate = Document(
		doc_type=source.doc_type,
		issue_date=timezone.localdate(),
		valid_until=source.valid_until,
		due_date=source.due_date,
		client_name=source.client_name,
		client_phone=source.client_phone,
		client_email=source.client_email,
		client_address=source.client_address,
		client_pin=source.client_pin,
		notes=source.notes,
		payment_terms=source.payment_terms,
		apply_vat=source.apply_vat,
		status=(
			Document.Status.DRAFT
			if source.doc_type == DocumentType.QUOTATION
			else Document.Status.UNPAID
		),
		created_by=request.user,
	)
	duplicate.save()
	for item in source.items.all():
		DocumentItem.objects.create(
			document=duplicate,
			description=item.description,
			quantity=item.quantity,
			unit_price=item.unit_price,
		)
	duplicate.recalculate_totals()
	messages.success(request, f"{duplicate.number} duplicated.")
	return redirect("documents:edit", pk=duplicate.pk)


@login_required
def document_convert(request, pk):
	quotation = get_object_or_404(Document.objects.prefetch_related("items"), pk=pk)
	if quotation.doc_type != DocumentType.QUOTATION:
		return HttpResponseForbidden("Only quotations can be converted into invoices.")
	if request.method != "POST":
		return redirect("documents:print", pk=quotation.pk)

	invoice = Document(
		doc_type=DocumentType.INVOICE,
		issue_date=timezone.localdate(),
		due_date=quotation.valid_until or (timezone.localdate() + timedelta(days=14)),
		client_name=quotation.client_name,
		client_phone=quotation.client_phone,
		client_email=quotation.client_email,
		client_address=quotation.client_address,
		client_pin=quotation.client_pin,
		notes=quotation.notes,
		payment_terms=quotation.payment_terms,
		apply_vat=quotation.apply_vat,
		status=Document.Status.UNPAID,
		created_by=request.user,
		converted_from=quotation,
	)
	invoice.save()
	for item in quotation.items.all():
		DocumentItem.objects.create(
			document=invoice,
			description=item.description,
			quantity=item.quantity,
			unit_price=item.unit_price,
		)
	invoice.recalculate_totals()
	quotation.status = Document.Status.CONVERTED
	quotation.save(update_fields=("status",))
	messages.success(request, f"{quotation.number} converted to {invoice.number}.")
	return redirect("documents:print", pk=invoice.pk)


@login_required
def document_mark_paid(request, pk):
	invoice = get_object_or_404(Document, pk=pk)
	if invoice.doc_type != DocumentType.INVOICE:
		return HttpResponseForbidden("Only invoices can be marked as paid.")
	if request.method != "POST":
		return redirect("documents:print", pk=invoice.pk)

	paid_date = request.POST.get("paid_date") or timezone.localdate().isoformat()
	payment_method = request.POST.get("payment_method", "").strip()
	if payment_method not in {choice[0] for choice in Document.PaymentMethod.choices}:
		messages.error(request, "Choose a valid payment method.")
		return redirect("documents:print", pk=invoice.pk)

	invoice.paid_date = paid_date
	invoice.payment_method = payment_method
	invoice.status = Document.Status.PAID
	invoice.save(update_fields=("paid_date", "payment_method", "status"))
	messages.success(request, f"{invoice.number} marked as paid.")
	return redirect("documents:print", pk=invoice.pk)


@login_required
def document_pdf(request, pk):
	document = get_object_or_404(Document.objects.prefetch_related("items"), pk=pk)
	context = _print_context(document)
	html = render(request, "documents/print.html", {**context, "pdf_mode": True})
	pdf = HTML(string=html.content.decode("utf-8"), base_url=request.build_absolute_uri("/")).write_pdf()
	response = HttpResponse(pdf, content_type="application/pdf")
	response["Content-Disposition"] = f'attachment; filename="{document.number}.pdf"'
	return response
