from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.inventory_list, name="list"),
    path("<int:pk>/edit/", views.inventory_edit, name="edit"),
    path("<int:pk>/delete/", views.inventory_delete, name="delete"),
    path("<int:pk>/restock/", views.inventory_restock, name="restock"),
    path("low-stock/", views.low_stock_list, name="low_stock"),
    path("recipes/", views.recipe_list, name="recipes"),
    path("recipes/<int:pk>/delete/", views.recipe_delete, name="recipe_delete"),
]
