from django.db import models


class InventoryItem(models.Model):
    name = models.CharField(max_length=150, unique=True)
    unit = models.CharField(max_length=30, help_text="e.g. kg, litre, piece")
    quantity_in_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.quantity_in_stock} {self.unit})"

    @property
    def is_low_stock(self):
        return self.quantity_in_stock <= self.reorder_level


class MenuItemIngredient(models.Model):
    """
    Links a MenuItem to the InventoryItem(s) it consumes, and how much of
    each is used per single order of that menu item. This is what powers
    automatic stock deduction when an order is confirmed.
    """
    menu_item = models.ForeignKey("menu.MenuItem", on_delete=models.CASCADE, related_name="ingredients")
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="used_in")
    quantity_required = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("menu_item", "inventory_item")

    def __str__(self):
        return f"{self.menu_item.name} needs {self.quantity_required} {self.inventory_item.unit} of {self.inventory_item.name}"


class InventoryLog(models.Model):
    ACTION_CHOICES = [
        ("restock", "Restock"),
        ("deduction", "Order Deduction"),
        ("adjustment", "Manual Adjustment"),
        ("return", "Return from Cancelled Order"),
    ]

    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="logs")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    change_qty = models.DecimalField(max_digits=10, decimal_places=2)  # positive=added, negative=removed
    reference_order = models.ForeignKey(
        "orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="inventory_logs"
    )
    note = models.CharField(max_length=255, blank=True)
    changed_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action}: {self.change_qty} {self.inventory_item.unit} of {self.inventory_item.name}"
