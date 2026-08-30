from django.contrib import admin
from .models import InventoryItem, MenuItemIngredient, InventoryLog


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "quantity_in_stock", "unit", "reorder_level", "is_low_stock")
    search_fields = ("name",)


@admin.register(MenuItemIngredient)
class MenuItemIngredientAdmin(admin.ModelAdmin):
    list_display = ("menu_item", "inventory_item", "quantity_required")


@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ("inventory_item", "action", "change_qty", "reference_order", "timestamp")
    list_filter = ("action",)
    readonly_fields = [f.name for f in InventoryLog._meta.fields]
