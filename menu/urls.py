from django.urls import path

from . import views

app_name = "menu"

urlpatterns = [
    path("", views.menu_list, name="list"),
    path("item/<int:pk>/", views.menu_item_detail, name="detail"),

    path("staff/categories/", views.category_list, name="category_list"),
    path("staff/categories/<int:pk>/delete/", views.category_delete, name="category_delete"),

    path("staff/items/", views.item_list, name="item_list"),
    path("staff/items/add/", views.item_form, name="item_add"),
    path("staff/items/<int:pk>/edit/", views.item_form, name="item_edit"),
    path("staff/items/<int:pk>/delete/", views.item_delete, name="item_delete"),
]
