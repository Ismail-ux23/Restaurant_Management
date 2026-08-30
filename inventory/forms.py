from django import forms

from .models import InventoryItem, MenuItemIngredient


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ["name", "unit", "quantity_in_stock", "reorder_level"]


class RestockForm(forms.Form):
    quantity = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    note = forms.CharField(max_length=255, required=False)


class MenuItemIngredientForm(forms.ModelForm):
    class Meta:
        model = MenuItemIngredient
        fields = ["menu_item", "inventory_item", "quantity_required"]
