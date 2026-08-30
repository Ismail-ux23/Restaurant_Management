from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.decorators import staff_required
from menu.models import MenuItem
from .models import Cart, CartItem, Order, OrderItem, Payment, Review
from .forms import CheckoutForm, ReviewForm, StatusChangeForm
from .services import change_order_status, apply_coupon_to_order, InsufficientStockError


def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(customer=user)
    return cart


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------

@login_required
def cart_view(request):
    cart = _get_cart(request.user)
    return render(request, "orders/cart.html", {"cart": cart})


@login_required
def cart_add(request, item_id):
    item = get_object_or_404(MenuItem, pk=item_id, is_available=True)
    cart = _get_cart(request.user)

    line, created = CartItem.objects.get_or_create(cart=cart, menu_item=item, defaults={"quantity": 1})
    if not created:
        line.quantity += 1
        line.save()

    messages.success(request, f"Added {item.name} to your cart.")
    return redirect(request.META.get("HTTP_REFERER", "menu:list"))


@login_required
def cart_update(request, item_id):
    cart = _get_cart(request.user)
    line = get_object_or_404(CartItem, cart=cart, menu_item_id=item_id)

    if request.method == "POST":
        try:
            qty = int(request.POST.get("quantity", 1))
        except ValueError:
            qty = 1

        if qty <= 0:
            line.delete()
        else:
            line.quantity = qty
            line.save()

    return redirect("orders:cart")


@login_required
def cart_remove(request, item_id):
    cart = _get_cart(request.user)
    CartItem.objects.filter(cart=cart, menu_item_id=item_id).delete()
    return redirect("orders:cart")


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

@login_required
def checkout(request):
    cart = _get_cart(request.user)
    if not cart.items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("menu:list")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = Order.objects.create(
                    customer=request.user,
                    order_type=form.cleaned_data["order_type"],
                    table=form.cleaned_data.get("table"),
                    delivery_address=form.cleaned_data.get("delivery_address", ""),
                )

                for line in cart.items.select_related("menu_item"):
                    OrderItem.objects.create(
                        order=order,
                        menu_item=line.menu_item,
                        quantity=line.quantity,
                        unit_price=line.menu_item.price,
                    )

                order.recalculate_totals()

                coupon_code = form.cleaned_data.get("coupon_code", "").strip()
                if coupon_code:
                    success, message = apply_coupon_to_order(order, coupon_code)
                    if not success:
                        messages.warning(request, f"Coupon not applied: {message}")

                order.save()

                if order.order_type == "dine_in" and order.table:
                    order.table.status = "occupied"
                    order.table.save()

                Payment.objects.create(
                    order=order,
                    method=form.cleaned_data["payment_method"],
                    amount=order.total_amount,
                    status="pending",
                )

                from .models import OrderStatusLog
                OrderStatusLog.objects.create(order=order, from_status="", to_status="pending", changed_by=request.user, note="Order placed")

                cart.items.all().delete()

            messages.success(request, f"Order #{order.id} placed! We'll confirm it shortly.")
            return redirect("orders:detail", pk=order.id)
    else:
        form = CheckoutForm()

    return render(request, "orders/checkout.html", {"form": form, "cart": cart})


# ---------------------------------------------------------------------------
# Customer order history / detail
# ---------------------------------------------------------------------------

@login_required
def order_history(request):
    orders = Order.objects.filter(customer=request.user).select_related("table", "payment")
    return render(request, "orders/order_history.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if order.customer_id != request.user.id and not request.user.is_staff:
        messages.error(request, "You don't have permission to view that order.")
        return redirect("orders:history")

    return render(request, "orders/order_detail.html", {
        "order": order,
        "status_form": StatusChangeForm(),
        "possible_next_statuses": order.STATUS_FLOW.get(order.status, []),
    })


@login_required
def cancel_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if order.customer_id != request.user.id and not request.user.is_staff:
        messages.error(request, "You don't have permission to modify that order.")
        return redirect("orders:history")

    if request.method == "POST":
        try:
            change_order_status(order, "cancelled", user=request.user, note="Cancelled by customer" if not request.user.is_staff else "Cancelled by staff")
            messages.success(request, "Order cancelled.")
        except ValueError as e:
            messages.error(request, str(e))

    return redirect("orders:detail", pk=order.id)


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

@login_required
def add_review(request, item_id):
    menu_item = get_object_or_404(MenuItem, pk=item_id)

    has_completed_order = OrderItem.objects.filter(
        order__customer=request.user, order__status="completed", menu_item=menu_item
    ).exists()
    if not has_completed_order:
        messages.error(request, "You can only review items from a completed order.")
        return redirect("menu:detail", pk=item_id)

    if Review.objects.filter(customer=request.user, menu_item=menu_item).exists():
        messages.error(request, "You've already reviewed this item.")
        return redirect("menu:detail", pk=item_id)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.customer = request.user
            review.menu_item = menu_item
            review.save()
            messages.success(request, "Thanks for your review!")
            return redirect("menu:detail", pk=item_id)
    else:
        form = ReviewForm()

    return render(request, "orders/review_form.html", {"form": form, "menu_item": menu_item})


# ---------------------------------------------------------------------------
# Staff: order queue & status management
# ---------------------------------------------------------------------------

@staff_required
def staff_order_queue(request):
    active_orders = Order.objects.exclude(status__in=["completed", "cancelled"]).select_related("customer", "table")
    return render(request, "orders/staff_order_queue.html", {"orders": active_orders})


@staff_required
def staff_all_orders(request):
    orders = Order.objects.select_related("customer", "table").all()
    status_filter = request.GET.get("status", "")
    if status_filter:
        orders = orders.filter(status=status_filter)
    return render(request, "orders/staff_all_orders.html", {
        "orders": orders, "status_filter": status_filter, "statuses": Order.STATUS_CHOICES,
    })


@staff_required
def staff_change_status(request, pk, new_status):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        note = request.POST.get("note", "")
        try:
            change_order_status(order, new_status, user=request.user, note=note)
            messages.success(request, f"Order #{order.id} moved to {order.get_status_display()}.")
        except InsufficientStockError as e:
            messages.error(request, str(e))
        except ValueError as e:
            messages.error(request, str(e))

    return redirect("orders:detail", pk=order.id)


@staff_required
def staff_mark_paid(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        payment = getattr(order, "payment", None)
        if payment:
            payment.status = "paid"
            payment.paid_at = timezone.now()
            payment.save()
            messages.success(request, f"Payment for Order #{order.id} marked as paid.")
    return redirect("orders:detail", pk=order.id)
