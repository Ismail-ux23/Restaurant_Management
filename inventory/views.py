from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import staff_required
from .models import InventoryItem, InventoryLog, MenuItemIngredient
from .forms import InventoryItemForm, RestockForm, MenuItemIngredientForm


@staff_required
def inventory_list(request):
    items = InventoryItem.objects.all()
    if request.method == "POST":
        form = InventoryItemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Inventory item added.")
            return redirect("inventory:list")
    else:
        form = InventoryItemForm()

    return render(request, "inventory/inventory_list.html", {"items": items, "form": form})


@staff_required
def inventory_edit(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == "POST":
        form = InventoryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Inventory item updated.")
            return redirect("inventory:list")
    else:
        form = InventoryItemForm(instance=item)
    return render(request, "inventory/inventory_form.html", {"form": form, "item": item})


@staff_required
def inventory_delete(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == "POST":
        item.delete()
        messages.success(request, "Inventory item deleted.")
    return redirect("inventory:list")


@staff_required
def inventory_restock(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == "POST":
        form = RestockForm(request.POST)
        if form.is_valid():
            qty = form.cleaned_data["quantity"]
            item.quantity_in_stock += qty
            item.save()
            InventoryLog.objects.create(
                inventory_item=item,
                action="restock",
                change_qty=qty,
                note=form.cleaned_data.get("note", ""),
                changed_by=request.user,
            )
            messages.success(request, f"Restocked {qty} {item.unit} of {item.name}.")
            return redirect("inventory:list")
    else:
        form = RestockForm()
    return render(request, "inventory/restock_form.html", {"form": form, "item": item})


@staff_required
def low_stock_list(request):
    items = [i for i in InventoryItem.objects.all() if i.is_low_stock]
    return render(request, "inventory/low_stock_list.html", {"items": items})


@staff_required
def recipe_list(request):
    """Manage which inventory items each menu item consumes."""
    links = MenuItemIngredient.objects.select_related("menu_item", "inventory_item").all()
    if request.method == "POST":
        form = MenuItemIngredientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Ingredient link added.")
            return redirect("inventory:recipes")
    else:
        form = MenuItemIngredientForm()
    return render(request, "inventory/recipe_list.html", {"links": links, "form": form})


@staff_required
def recipe_delete(request, pk):
    link = get_object_or_404(MenuItemIngredient, pk=pk)
    if request.method == "POST":
        link.delete()
        messages.success(request, "Ingredient link removed.")
    return redirect("inventory:recipes")
