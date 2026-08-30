from django.contrib import admin
from .models import Cart, CartItem, Coupon, Order, OrderItem, OrderStatusLog, Payment, Review


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "order_type", "status", "total_amount", "created_at")
    list_filter = ("status", "order_type")
    search_fields = ("customer__username", "customer__email")
    inlines = [OrderItemInline, PaymentInline]
    readonly_fields = ("subtotal", "discount_amount", "total_amount")


@admin.register(OrderStatusLog)
class OrderStatusLogAdmin(admin.ModelAdmin):
    list_display = ("order", "from_status", "to_status", "changed_by", "timestamp")
    readonly_fields = [f.name for f in OrderStatusLog._meta.fields]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_percent", "active", "valid_from", "valid_to", "times_used", "usage_limit")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("customer", "menu_item", "rating", "created_at")
    list_filter = ("rating",)


admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Payment)
