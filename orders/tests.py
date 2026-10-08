from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection, close_old_connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from inventory.models import InventoryItem, InventoryLog, MenuItemIngredient
from menu.models import MenuItem
from tables.models import Table
from .models import Order, OrderItem, OrderStatusLog
from .services import change_order_status, InsufficientStockError, restore_inventory_for_order


def fixtures():
    user = get_user_model().objects.create_user(username='customer')
    ingredient = InventoryItem.objects.create(name='Flour', unit='kg', quantity_in_stock=10)
    item = MenuItem.objects.create(name='Bread', price=Decimal('5'))
    recipe = MenuItemIngredient.objects.create(menu_item=item, inventory_item=ingredient, quantity_required=2)
    table = Table.objects.create(number=1, status='occupied')
    order = Order.objects.create(customer=user, order_type='dine_in', table=table)
    line = OrderItem.objects.create(order=order, menu_item=item, quantity=2, unit_price=item.price)
    return user, ingredient, item, recipe, table, order, line


class OrderLifecycleTests(TestCase):
    def setUp(self):
        self.user, self.ingredient, self.item, self.recipe, self.table, self.order, self.line = fixtures()

    def balance(self):
        self.ingredient.refresh_from_db()
        return self.ingredient.quantity_in_stock

    def test_stale_duplicate_confirmation_cannot_deduct_twice(self):
        stale = Order.objects.get(pk=self.order.pk)
        change_order_status(self.order, 'confirmed', user=self.user)
        with self.assertRaises(ValueError):
            change_order_status(stale, 'confirmed', user=self.user)
        self.assertEqual(self.balance(), 6)
        self.assertEqual(InventoryLog.objects.filter(action='deduction').count(), 1)
        self.assertEqual(OrderStatusLog.objects.count(), 1)

    def test_stale_cancellation_cannot_return_twice(self):
        change_order_status(self.order, 'confirmed')
        stale = Order.objects.get(pk=self.order.pk)
        change_order_status(Order.objects.get(pk=self.order.pk), 'cancelled')
        with self.assertRaises(ValueError):
            change_order_status(stale, 'cancelled')
        self.assertEqual(self.balance(), 10)
        self.assertEqual(InventoryLog.objects.filter(action='return').count(), 1)

    def test_recipe_changes_do_not_change_returned_stock(self):
        change_order_status(self.order, 'confirmed')
        self.recipe.quantity_required = 7
        self.recipe.save()
        self.line.quantity = 3
        self.line.save()
        change_order_status(self.order, 'cancelled')
        self.assertEqual(self.balance(), 10)
        self.assertEqual(InventoryLog.objects.get(action='return').change_qty, 4)

    def test_deleted_recipe_still_returns_recorded_deduction(self):
        change_order_status(self.order, 'confirmed')
        self.recipe.delete()
        change_order_status(self.order, 'cancelled')
        self.assertEqual(self.balance(), 10)

    def test_restore_helper_only_returns_outstanding_deductions(self):
        change_order_status(self.order, 'confirmed')
        restore_inventory_for_order(self.order)
        restore_inventory_for_order(self.order)
        self.assertEqual(self.balance(), 10)
        self.assertEqual(InventoryLog.objects.filter(action='return').count(), 1)

    def test_pending_cancellation_changes_no_inventory_and_releases_table(self):
        change_order_status(self.order, 'cancelled')
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, 'available')
        self.assertEqual(self.balance(), 10)
        self.assertFalse(InventoryLog.objects.exists())

    def test_shortage_rolls_back_every_ingredient_and_status(self):
        short = InventoryItem.objects.create(name='Salt', unit='kg', quantity_in_stock=0)
        MenuItemIngredient.objects.create(menu_item=self.item, inventory_item=short, quantity_required=1)
        with self.assertRaises(InsufficientStockError):
            change_order_status(self.order, 'confirmed')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'pending')
        self.assertEqual(self.balance(), 10)
        self.assertFalse(InventoryLog.objects.exists())
        self.assertFalse(OrderStatusLog.objects.exists())

    def test_status_audit_failure_rolls_back_inventory(self):
        with patch('orders.services.OrderStatusLog.objects.create', side_effect=RuntimeError('audit failure')):
            with self.assertRaises(RuntimeError):
                change_order_status(self.order, 'confirmed')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'pending')
        self.assertEqual(self.balance(), 10)
        self.assertFalse(InventoryLog.objects.exists())

    def test_inventory_audit_failure_rolls_back_status(self):
        with patch('orders.services.InventoryLog.objects.create', side_effect=RuntimeError('audit failure')):
            with self.assertRaises(RuntimeError):
                change_order_status(self.order, 'confirmed')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'pending')
        self.assertEqual(self.balance(), 10)

    def test_normal_lifecycle_deducts_once_and_releases_table(self):
        for status in ['confirmed', 'preparing', 'ready', 'completed']:
            result = change_order_status(self.order, status)
            self.assertEqual(result.status, status)
        self.assertEqual(self.balance(), 6)
        self.assertEqual(InventoryLog.objects.count(), 1)
        self.assertEqual(OrderStatusLog.objects.count(), 4)
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, 'available')
        with self.assertRaises(ValueError):
            change_order_status(self.order, 'cancelled')

    def test_invalid_recipe_cannot_increase_stock(self):
        self.recipe.quantity_required = -1
        self.recipe.save()
        with self.assertRaises(ValueError):
            change_order_status(self.order, 'confirmed')
        self.assertEqual(self.balance(), 10)


class ConcurrentConfirmationTests(TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_two_staff_confirm_same_order_only_once(self):
        _, ingredient, _, _, _, order, _ = fixtures()
        barrier = Barrier(2)
        def confirm():
            close_old_connections()
            try:
                stale = Order.objects.get(pk=order.pk)
                barrier.wait(timeout=10)
                try:
                    change_order_status(stale, 'confirmed')
                    return 'confirmed'
                except ValueError:
                    return 'rejected'
            finally:
                connection.close()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: confirm(), range(2)))
        self.assertCountEqual(results, ['confirmed', 'rejected'])
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.quantity_in_stock, 6)
        self.assertEqual(InventoryLog.objects.count(), 1)
        self.assertEqual(OrderStatusLog.objects.count(), 1)
