from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import staff_required
from .models import Category, MenuItem
from .forms import CategoryForm, MenuItemForm


# ---------------------------------------------------------------------------
# Customer-facing views
# ---------------------------------------------------------------------------

def menu_list(request):
    items = MenuItem.objects.filter(is_available=True).select_related("category")

    search = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")

    if search:
        items = items.filter(name__icontains=search)

    if category_id:
        items = items.filter(category_id=category_id)

    categories = Category.objects.all()

    return render(request, "menu/menu_list.html", {
        "items": items,
        "categories": categories,
        "search": search,
        "selected_category": category_id,
    })


def menu_item_detail(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    reviews = item.reviews.select_related("customer").order_by("-created_at")
    return render(request, "menu/menu_item_detail.html", {"item": item, "reviews": reviews})


# ---------------------------------------------------------------------------
# Staff: category management
# ---------------------------------------------------------------------------

@staff_required
def category_list(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category added.")
            return redirect("menu:category_list")
    else:
        form = CategoryForm()

    categories = Category.objects.all()
    return render(request, "menu/category_list.html", {"categories": categories, "form": form})


@staff_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        category.delete()
        messages.success(request, "Category deleted.")
    return redirect("menu:category_list")


# ---------------------------------------------------------------------------
# Staff: menu item management
# ---------------------------------------------------------------------------

@staff_required
def item_list(request):
    items = MenuItem.objects.select_related("category").all()
    return render(request, "menu/item_list.html", {"items": items})


@staff_required
def item_form(request, pk=None):
    item = get_object_or_404(MenuItem, pk=pk) if pk else None

    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"Menu item {'updated' if item else 'added'}.")
            return redirect("menu:item_list")
    else:
        form = MenuItemForm(instance=item)

    return render(request, "menu/item_form.html", {"form": form, "item": item})


@staff_required
def item_delete(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    if request.method == "POST":
        item.delete()
        messages.success(request, "Menu item deleted.")
    return redirect("menu:item_list")
