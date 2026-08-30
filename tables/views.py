from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import staff_required
from .models import Table
from .forms import TableForm


@staff_required
def table_list(request):
    if request.method == "POST":
        form = TableForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Table added.")
            return redirect("tables:list")
    else:
        form = TableForm()

    tables = Table.objects.all()
    return render(request, "tables/table_list.html", {"tables": tables, "form": form})


@staff_required
def table_edit(request, pk):
    table = get_object_or_404(Table, pk=pk)
    if request.method == "POST":
        form = TableForm(request.POST, instance=table)
        if form.is_valid():
            form.save()
            messages.success(request, "Table updated.")
            return redirect("tables:list")
    else:
        form = TableForm(instance=table)
    return render(request, "tables/table_form.html", {"form": form, "table": table})


@staff_required
def table_delete(request, pk):
    table = get_object_or_404(Table, pk=pk)
    if request.method == "POST":
        table.delete()
        messages.success(request, "Table deleted.")
    return redirect("tables:list")
