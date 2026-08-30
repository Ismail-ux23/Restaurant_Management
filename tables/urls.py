from django.urls import path

from . import views

app_name = "tables"

urlpatterns = [
    path("", views.table_list, name="list"),
    path("<int:pk>/edit/", views.table_edit, name="edit"),
    path("<int:pk>/delete/", views.table_delete, name="delete"),
]
