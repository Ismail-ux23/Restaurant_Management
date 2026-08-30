from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("sales/", views.sales_report, name="sales_report"),
]
