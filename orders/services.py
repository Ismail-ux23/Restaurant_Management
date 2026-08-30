from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from inventory.models import MenuItemIngredient, InventoryLog
from .models import OrderStatusLog


class InsufficientStockError(Exception):
    """Raised when an order can't be confirmed because ingredients are short."""


def _required_ingredients_for_order(order):
    """
    Returns {inventory_item: total_quantity_needed} across every line item
    in the order, based on each menu item's linked ingredients.
    """
    needed = {}
    for line in order.items.select_related("menu_item"):
        recipe_lines = MenuItemIngredient.objects.filter(menu_item=line.menu_item).select_related("inventory_item")
        for recipe_line in recipe_lines:
            qty = recipe_line.quantity_required * line.quantity
            needed[recipe_line.inventory_item] = needed.get(recipe_line.inventory_item, Decimal("0")) + qty
    return needed


@transaction.atomic
def deduct_inventory_for_order(order, user=None):
    """
    Checks that enough stock exists for every ingredient this order needs,
    and if so, deducts it all atomically and logs each deduction. Raises
    InsufficientStockError (without changing anything) if any ingredient
    is short.
    """
    needed = _required_ingredients_for_order(order)

    shortages = []
    for inventory_item, qty_needed in needed.items():
        # lock the row to avoid a race between two orders confirming at once
        locked_item = type(inventory_item).objects.select_for_update().get(pk=inventory_item.pk)
        if locked_item.quantity_in_stock < qty_needed:
            shortages.append(f"{locked_item.name} (need {qty_needed} {locked_item.unit}, have {locked_item.quantity_in_stock})")

    if shortages:
        raise InsufficientStockError("Not enough stock: " + "; ".join(shortages))

    for inventory_item, qty_needed in needed.items():
        locked_item = type(inventory_item).objects.select_for_update().get(pk=inventory_item.pk)
        locked_item.quantity_in_stock -= qty_needed
        locked_item.save()
        InventoryLog.objects.create(
            inventory_item=locked_item,
            action="deduction",
            change_qty=-qty_needed,
            reference_order=order,
            note=f"Order #{order.id} confirmed",
            changed_by=user,
        )


@transaction.atomic
def restore_inventory_for_order(order, user=None):
    """Returns stock to inventory for an order that had already been
    confirmed (and therefore deducted) but is now being cancelled."""
    needed = _required_ingredients_for_order(order)
    for inventory_item, qty in needed.items():
        locked_item = type(inventory_item).objects.select_for_update().get(pk=inventory_item.pk)
        locked_item.quantity_in_stock += qty
        locked_item.save()
        InventoryLog.objects.create(
            inventory_item=locked_item,
            action="return",
            change_qty=qty,
            reference_order=order,
            note=f"Order #{order.id} cancelled — stock returned",
            changed_by=user,
        )


@transaction.atomic
def change_order_status(order, new_status, user=None, note=""):
    """
    The single entry point for moving an order through its lifecycle.
    Enforces the legal state machine, handles inventory deduction on
    confirmation, inventory restoration + table release on cancellation,
    and always writes an OrderStatusLog entry.
    """
    if not order.can_transition_to(new_status):
        raise ValueError(f"Cannot move an order from '{order.status}' to '{new_status}'.")

    old_status = order.status
    inventory_was_deducted = old_status in ("confirmed", "preparing", "ready")

    if new_status == "confirmed":
        deduct_inventory_for_order(order, user=user)

    if new_status == "cancelled" and inventory_was_deducted:
        restore_inventory_for_order(order, user=user)

    if new_status in ("completed", "cancelled") and order.table_id:
        order.table.status = "available"
        order.table.save()

    order.status = new_status
    order.save()

    OrderStatusLog.objects.create(
        order=order,
        from_status=old_status,
        to_status=new_status,
        changed_by=user,
        note=note,
    )
    return order


def apply_coupon_to_order(order, code):
    """Validates a coupon code and, if valid, attaches it to the order and
    recalculates totals. Returns (success: bool, message: str)."""
    from .models import Coupon

    try:
        coupon = Coupon.objects.get(code__iexact=code.strip())
    except Coupon.DoesNotExist:
        return False, "That coupon code doesn't exist."

    is_valid, reason = coupon.is_valid()
    if not is_valid:
        return False, reason

    order.coupon = coupon
    order.recalculate_totals()
    order.save()
    return True, f"Coupon applied: {coupon.discount_percent}% off."
