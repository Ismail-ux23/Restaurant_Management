from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:item_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:item_id>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:item_id>/", views.cart_remove, name="cart_remove"),

    path("checkout/", views.checkout, name="checkout"),

    path("history/", views.order_history, name="history"),
    path("<int:pk>/", views.order_detail, name="detail"),
    path("<int:pk>/cancel/", views.cancel_order, name="cancel"),

    path("item/<int:item_id>/review/", views.add_review, name="add_review"),

    path("staff/queue/", views.staff_order_queue, name="staff_queue"),
    path("staff/all/", views.staff_all_orders, name="staff_all"),
    path("staff/<int:pk>/status/<str:new_status>/", views.staff_change_status, name="staff_change_status"),
    path("staff/<int:pk>/mark-paid/", views.staff_mark_paid, name="staff_mark_paid"),
]
