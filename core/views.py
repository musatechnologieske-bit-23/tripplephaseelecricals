from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone

from documents.models import Document, DocumentType

from .forms import CompanySettingsForm
from .models import CompanySettings


@login_required
def home(request):
    CompanySettings.load()
    today = timezone.localdate()

    total_quotations = Document.objects.filter(
        doc_type=DocumentType.QUOTATION,
        issue_date__year=today.year,
        issue_date__month=today.month,
    )
    total_invoices = Document.objects.filter(
        doc_type=DocumentType.INVOICE,
        issue_date__year=today.year,
        issue_date__month=today.month,
    )

    quoted_total = total_quotations.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    invoiced_total = total_invoices.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    paid_total = total_invoices.filter(status=Document.Status.PAID).aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    outstanding_total = invoiced_total - paid_total
    vat_total = total_invoices.aggregate(vat=Sum("vat_amount"))["vat"] or Decimal("0.00")
    current_month_document_count = Document.objects.filter(
        issue_date__year=today.year,
        issue_date__month=today.month,
    ).count()

    stats = {
        "quoted_total": quoted_total,
        "invoiced_total": invoiced_total,
        "paid_total": paid_total,
        "outstanding_total": outstanding_total,
        "vat_total": vat_total,
        "document_count": current_month_document_count,
        "quoted_count": total_quotations.count(),
        "invoiced_count": total_invoices.count(),
        "paid_count": total_invoices.filter(status=Document.Status.PAID).count(),
    }

    return render(
        request,
        "core/home.html",
        {
            "stats": stats,
        },
    )


@login_required
def company_settings(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Superuser access required.")

    settings = CompanySettings.load()
    if request.method == "POST":
        form = CompanySettingsForm(request.POST, request.FILES, instance=settings)
        if form.is_valid():
            form.save()
            return redirect("company-settings")
    else:
        form = CompanySettingsForm(instance=settings)
    return render(request, "core/company_settings_form.html", {"form": form})
