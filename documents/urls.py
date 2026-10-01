from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("", views.document_list, name="list"),
    path("new/", views.document_form, name="create"),
    path("<int:pk>/print/", views.document_print, name="print"),
    path("<int:pk>/pdf/", views.document_pdf, name="pdf"),
    path("<int:pk>/duplicate/", views.document_duplicate, name="duplicate"),
    path("<int:pk>/convert/", views.document_convert, name="convert"),
    path("<int:pk>/mark-paid/", views.document_mark_paid, name="mark-paid"),
    path("<int:pk>/edit/", views.document_form, name="edit"),
]