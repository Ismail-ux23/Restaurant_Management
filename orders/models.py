from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class Cart(models.Model):
    customer = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def subtotal(self):
        return sum((line.subtotal for line in self.items.all()), Decimal("0.00"))

    @property
    def item_count(self):
        return sum(line.quantity for line in self.items.all())

    def __str__(self):
        return f"Cart<{self.customer.username}>"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey("menu.MenuItem", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cart", "menu_item")

    @property
    def subtotal(self):
        return self.menu_item.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name}"


class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True)
    discount_percent = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    times_used = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.code} (-{self.discount_percent}%)"

    def is_valid(self):
        now = timezone.now()
        if not self.active:
            return False, "This coupon is not active."
        if not (self.valid_from <= now <= self.valid_to):
            return False, "This coupon is expired or not yet active."
        if self.usage_limit and self.times_used >= self.usage_limit:
            return False, "This coupon has reached its usage limit."
        return True, ""


class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ("dine_in", "Dine-in"),
        ("takeaway", "Takeaway"),
        ("delivery", "Delivery"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("preparing", "Preparing"),
        ("ready", "Ready"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    # Forward-only status flow, except cancellation which is allowed from
    # any non-terminal state.
    STATUS_FLOW = {
        "pending": ["confirmed", "cancelled"],
        "confirmed": ["preparing", "cancelled"],
        "preparing": ["ready", "cancelled"],
        "ready": ["completed", "cancelled"],
        "completed": [],
        "cancelled": [],
    }

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    table = models.ForeignKey("tables.Table", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    delivery_address = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} ({self.get_status_display()})"

    def can_transition_to(self, new_status):
        return new_status in self.STATUS_FLOW.get(self.status, [])

    def recalculate_totals(self):
        self.subtotal = sum((line.subtotal for line in self.items.all()), Decimal("0.00"))
        if self.coupon:
            self.discount_amount = (self.subtotal * self.coupon.discount_percent / Decimal("100")).quantize(Decimal("0.01"))
        else:
            self.discount_amount = Decimal("0.00")
        self.total_amount = self.subtotal - self.discount_amount


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey("menu.MenuItem", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name}"


class OrderStatusLog(models.Model):
    """Audit trail of every status change on an order — mirrors the
    StockLog / AppointmentLog pattern used in the other projects."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_logs")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    note = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"Order #{self.order_id}: {self.from_status} -> {self.to_status}"


class Payment(models.Model):
    METHOD_CHOICES = [("cash", "Cash"), ("card", "Card")]
    STATUS_CHOICES = [("pending", "Pending"), ("paid", "Paid"), ("failed", "Failed")]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="cash")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment for Order #{self.order_id} ({self.status})"


class Review(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    menu_item = models.ForeignKey("menu.MenuItem", on_delete=models.CASCADE, related_name="reviews")
    order_item = models.ForeignKey(OrderItem, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("customer", "menu_item")

    def __str__(self):
        return f"{self.customer.username} rated {self.menu_item.name}: {self.rating}/5"
