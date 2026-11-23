from html import escape
from io import BytesIO
from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
	Image,
	Paragraph,
	SimpleDocTemplate,
	Spacer,
	Table,
	TableStyle,
)


RED = colors.HexColor("#E10600")
INK = colors.HexColor("#171717")
MUTED = colors.HexColor("#555555")
LINE = colors.HexColor("#D9DCE5")


def _paragraph(text, style):
	markup = escape(str(text or "")).replace("\n", "<br/>")
	return Paragraph(markup, style)


def _money(amount):
	return f"KES {amount:,.2f}"


def _date(value):
	return value.strftime("%d %b %Y") if value else ""


def _page_number(canvas, document):
	canvas.saveState()
	canvas.setFont("Helvetica", 8)
	canvas.setFillColor(MUTED)
	canvas.drawRightString(A4[0] - 14 * mm, 8 * mm, f"Page {document.page}")
	canvas.restoreState()


def render_document_pdf(document, company):
	styles = getSampleStyleSheet()
	styles.add(
		ParagraphStyle(
			name="Company", parent=styles["Normal"], fontSize=8, leading=11, textColor=MUTED
		)
	)
	styles.add(
		ParagraphStyle(
			name="Heading", parent=styles["Normal"], fontSize=17, leading=20,
			textColor=RED, alignment=TA_RIGHT, fontName="Helvetica-Bold",
		)
	)
	styles.add(
		ParagraphStyle(
			name="InvoiceHeading", parent=styles["Heading"], textColor=INK,
		)
	)
	styles.add(
		ParagraphStyle(
			name="CompanyName", parent=styles["Normal"], fontSize=9, leading=12,
			textColor=INK, fontName="Helvetica-Bold",
		)
	)
	styles.add(
		ParagraphStyle(
			name="DocNumber", parent=styles["Normal"], fontSize=10, leading=13,
			alignment=TA_RIGHT, fontName="Helvetica-Bold",
		)
	)
	styles.add(
		ParagraphStyle(
			name="SmallRight", parent=styles["Normal"], fontSize=8, leading=11,
			textColor=MUTED, alignment=TA_RIGHT,
		)
	)
	styles.add(
		ParagraphStyle(
			name="Eyebrow", parent=styles["Normal"], fontSize=7, leading=9,
			textColor=MUTED, fontName="Helvetica-Bold",
		)
	)
	styles.add(
		ParagraphStyle(
			name="Client", parent=styles["Normal"], fontSize=11, leading=14,
			fontName="Helvetica-Bold",
		)
	)
	styles.add(
		ParagraphStyle(name="BodySmall", parent=styles["Normal"], fontSize=8, leading=11, textColor=INK)
	)
	styles.add(
		ParagraphStyle(
			name="TableHeader", parent=styles["Normal"], fontSize=7, leading=9,
			textColor=colors.white, fontName="Helvetica-Bold",
		)
	)
	styles.add(ParagraphStyle(name="TableCell", parent=styles["Normal"], fontSize=8, leading=10))
	styles.add(ParagraphStyle(name="TableNumber", parent=styles["TableCell"], alignment=TA_RIGHT))
	styles.add(
		ParagraphStyle(name="TotalLabel", parent=styles["Normal"], fontSize=9, leading=12, textColor=MUTED)
	)
	styles.add(
		ParagraphStyle(
			name="TotalValue", parent=styles["Normal"], fontSize=9, leading=12, alignment=TA_RIGHT
		)
	)
	styles.add(
		ParagraphStyle(
			name="GrandTotal", parent=styles["Normal"], fontSize=11, leading=14,
			fontName="Helvetica-Bold",
		)
	)
	styles.add(ParagraphStyle(name="GrandTotalValue", parent=styles["GrandTotal"], alignment=TA_RIGHT))
	styles.add(
		ParagraphStyle(name="SectionTitle", parent=styles["Normal"], fontSize=8, leading=10, fontName="Helvetica-Bold")
	)
	buffer = BytesIO()
	pdf = SimpleDocTemplate(
		buffer,
		pagesize=A4,
		rightMargin=14 * mm,
		leftMargin=14 * mm,
		topMargin=13 * mm,
		bottomMargin=16 * mm,
		title=f"{document.get_doc_type_display()} {document.number}",
		author=company.name,
	)
	width = A4[0] - 28 * mm
	logo_path = Path(settings.BASE_DIR) / "static" / "img" / "tripplephase-wordmark.png"
	logo = Image(str(logo_path), width=45 * mm, height=20 * mm, kind="proportional")

	doc_type = document.get_doc_type_display().upper()
	number_label = (
		f"Invoice No: {document.invoice_number or document.number}"
		if document.doc_type == "invoice"
		else f"Quotation No: {document.number}"
	)
	heading = [Paragraph(escape(number_label), styles["DocNumber"])]
	if document.lpo_number:
		heading.append(Paragraph(f"LPO No: {escape(document.lpo_number)}", styles["SmallRight"]))
	heading.append(
		Paragraph(
			escape(doc_type),
			styles["InvoiceHeading"] if document.doc_type == "invoice" else styles["Heading"],
		)
	)
	if document.doc_type == "quotation":
		heading.append(
			Paragraph(
				f"Payment term: {escape(document.get_payment_terms_display())}",
				styles["SmallRight"],
			)
		)

	company_contact = "\n".join(
		part
		for part in (
			company.address,
			company.phone,
			company.email,
			f"KRA PIN: {company.kra_pin}" if company.kra_pin else "",
		)
		if part
	)
	header = Table(
		[
			[
				[logo, _paragraph(company.name.title(), styles["CompanyName"]), _paragraph(company_contact, styles["Company"])],
				heading,
			]
		],
		colWidths=[width * 0.66, width * 0.34],
	)
	header.setStyle(
		TableStyle(
			[
				("VALIGN", (0, 0), (-1, -1), "TOP"),
				("ALIGN", (1, 0), (1, 0), "RIGHT"),
				("LINEBELOW", (0, 0), (-1, -1), 1.5, INK),
				("BOTTOMPADDING", (0, 0), (-1, -1), 10),
			]
		)
	)

	client_lines = [
		_paragraph(document.client_name, styles["Client"]),
	]
	client_details = "\n".join(
		part
		for part in (
			document.client_address,
			document.client_phone,
			document.client_email,
			document.client_pin,
		)
		if part
	)
	if client_details:
		client_lines.append(_paragraph(client_details, styles["BodySmall"]))

	date_lines = [
		f"<b>Issue date</b> &nbsp; {escape(_date(document.issue_date))}",
	]
	if document.doc_type == "quotation" and document.valid_until:
		date_lines.append(f"<b>Valid until</b> &nbsp; {escape(_date(document.valid_until))}")
	if document.doc_type == "invoice" and document.due_date:
		date_lines.append(f"<b>Due date</b> &nbsp; {escape(_date(document.due_date))}")
	if document.payment_terms:
		date_lines.append(f"<b>Payment term</b> &nbsp; {escape(document.get_payment_terms_display())}")
	dates = Paragraph("<br/>".join(date_lines), styles["SmallRight"])
	metadata = Table([[client_lines, dates]], colWidths=[width * 0.58, width * 0.42])
	metadata.setStyle(
		TableStyle(
			[
				("VALIGN", (0, 0), (-1, -1), "TOP"),
				("ALIGN", (1, 0), (1, 0), "RIGHT"),
				("TOPPADDING", (0, 0), (-1, -1), 12),
				("BOTTOMPADDING", (0, 0), (-1, -1), 8),
			]
		)
	)

	items = [[
		_paragraph("NO.", styles["TableHeader"]),
		_paragraph("DESCRIPTION", styles["TableHeader"]),
		_paragraph("QTY", styles["TableHeader"]),
		_paragraph("UNIT PRICE (KES)", styles["TableHeader"]),
		_paragraph("AMOUNT (KES)", styles["TableHeader"]),
	]]
	for index, item in enumerate(document.items.all(), start=1):
		items.append(
			[
				_paragraph(str(index), styles["TableNumber"]),
				_paragraph(item.description, styles["TableCell"]),
				_paragraph(f"{item.quantity:,.2f}", styles["TableNumber"]),
				_paragraph(f"{item.unit_price:,.2f}", styles["TableNumber"]),
				_paragraph(f"{item.line_total:,.2f}", styles["TableNumber"]),
			]
		)
	item_table = Table(
		items,
		colWidths=[width * 0.06, width * 0.42, width * 0.10, width * 0.20, width * 0.22],
		repeatRows=1,
		hAlign="LEFT",
	)
	item_table.setStyle(
		TableStyle(
			[
				("BACKGROUND", (0, 0), (-1, 0), INK),
				("VALIGN", (0, 0), (-1, -1), "TOP"),
				("LEFTPADDING", (0, 0), (-1, -1), 6),
				("RIGHTPADDING", (0, 0), (-1, -1), 6),
				("TOPPADDING", (0, 0), (-1, -1), 5),
				("BOTTOMPADDING", (0, 0), (-1, -1), 5),
				("LINEBELOW", (0, 1), (-1, -1), 0.5, LINE),
			]
		)
	)

	totals = [
		[
			_paragraph("Subtotal", styles["TotalLabel"]),
			_paragraph(_money(document.subtotal), styles["TotalValue"]),
		],
	]
	if document.apply_vat:
		totals.append(
			[
				_paragraph(f"VAT ({company.vat_rate}%)", styles["TotalLabel"]),
				_paragraph(_money(document.vat_amount), styles["TotalValue"]),
			]
		)
	totals.append(
		[
			_paragraph("Total", styles["GrandTotal"]),
			_paragraph(_money(document.total), styles["GrandTotalValue"]),
		]
	)
	totals_table = Table(totals, colWidths=[width * 0.35, width * 0.25], hAlign="RIGHT")
	totals_table.setStyle(
		TableStyle(
			[
				("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
				("TOPPADDING", (0, 0), (-1, -1), 3),
				("BOTTOMPADDING", (0, 0), (-1, -1), 3),
				("LINEABOVE", (0, -1), (-1, -1), 1, INK),
				("TOPPADDING", (0, -1), (-1, -1), 7),
			]
		)
	)

	details = Table(
		[
			[
				_paragraph("PAYABLE TO", styles["TableHeader"]),
				_paragraph("BANKING DETAILS", styles["TableHeader"]),
			],
			[
				[
					_paragraph(company.name, styles["SectionTitle"]),
					_paragraph(company.address, styles["BodySmall"]),
				],
				_paragraph(f"{company.payment_details}\nCurrency: KES", styles["BodySmall"]),
			],
		],
		colWidths=[width * 0.42, width * 0.58],
	)
	details.setStyle(
		TableStyle(
			[
				("BACKGROUND", (0, 0), (-1, 0), INK),
				("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#AEB9D0")),
				("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#AEB9D0")),
				("VALIGN", (0, 0), (-1, -1), "TOP"),
				("LEFTPADDING", (0, 0), (-1, -1), 6),
				("RIGHTPADDING", (0, 0), (-1, -1), 6),
				("TOPPADDING", (0, 0), (-1, -1), 5),
				("BOTTOMPADDING", (0, 0), (-1, -1), 5),
			]
		)
	)

	story = [header, Spacer(1, 4 * mm), metadata, item_table, Spacer(1, 2 * mm), totals_table]
	if document.notes:
		story.extend(
			[
				Spacer(1, 4 * mm),
				Paragraph("NOTES", styles["Eyebrow"]),
				_paragraph(document.notes, styles["BodySmall"]),
			]
		)
	if company.terms:
		story.extend(
			[
				Spacer(1, 3 * mm),
				Paragraph("TERMS &amp; CONDITIONS", styles["Eyebrow"]),
				_paragraph(company.terms, styles["BodySmall"]),
			]
		)
	story.extend([Spacer(1, 3 * mm), details])
	pdf.build(story, onFirstPage=_page_number, onLaterPages=_page_number)
	return buffer.getvalue()
