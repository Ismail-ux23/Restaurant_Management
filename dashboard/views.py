from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Count
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import staff_required
from orders.models import Order
from inventory.models import InventoryItem
from tables.models import Table


@staff_required
def home(request):
    today = timezone.now().date()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    today_end = today_start + timedelta(days=1)

    todays_orders = Order.objects.filter(created_at__gte=today_start, created_at__lt=today_end)
    todays_revenue = todays_orders.filter(status="completed").aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")

    pending_count = Order.objects.filter(status="pending").count()
    active_count = Order.objects.exclude(status__in=["completed", "cancelled"]).count()

    low_stock_items = [i for i in InventoryItem.objects.all() if i.is_low_stock]

    tables_summary = {
        "total": Table.objects.count(),
        "occupied": Table.objects.filter(status="occupied").count(),
        "available": Table.objects.filter(status="available").count(),
    }

    return render(request, "dashboard/home.html", {
        "todays_order_count": todays_orders.count(),
        "todays_revenue": todays_revenue,
        "pending_count": pending_count,
        "active_count": active_count,
        "low_stock_items": low_stock_items,
        "tables_summary": tables_summary,
    })


@staff_required
def sales_report(request):
    days = int(request.GET.get("days", 7))
    since = timezone.now() - timedelta(days=days)

    completed_orders = Order.objects.filter(status="completed", created_at__gte=since)

    total_revenue = completed_orders.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    total_orders = completed_orders.count()
    avg_order_value = (total_revenue / total_orders) if total_orders else Decimal("0.00")

    by_type = completed_orders.values("order_type").annotate(
        count=Count("id"), revenue=Sum("total_amount")
    ).order_by("-revenue")

    from django.db.models.functions import TruncDate
    by_day = (
        completed_orders
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(revenue=Sum("total_amount"), count=Count("id"))
        .order_by("day")
    )

    top_items = (
        Order.objects.filter(status="completed", created_at__gte=since)
        .prefetch_related("items")
    )
    item_totals = {}
    for order in top_items:
        for line in order.items.all():
            key = line.menu_item.name
            item_totals[key] = item_totals.get(key, 0) + line.quantity
    top_items_list = sorted(item_totals.items(), key=lambda x: x[1], reverse=True)[:10]

    return render(request, "dashboard/sales_report.html", {
        "days": days,
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "avg_order_value": avg_order_value,
        "by_type": by_type,
        "by_day": by_day,
        "top_items": top_items_list,
    })
