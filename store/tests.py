from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from store.models import Item, Batch

class ModelTests(TestCase):
    def setUp(self):
        self.item = Item.objects.create(
            name="Paracetamol 500mg",
            description="Pain relief",
            cost_price=Decimal("10.00"),
            selling_price=Decimal("15.00"),
        )
        self.batch1 = Batch.objects.create(
            item=self.item,
            quantity=20,
            expiry_date=date.today() + timedelta(days=30),
        )
        self.batch2 = Batch.objects.create(
            item=self.item,
            quantity=30,
            expiry_date=date.today() + timedelta(days=60),
        )

    def test_item_properties(self):
        self.assertEqual(self.item.total_quantity(), 50)
        self.assertEqual(self.item.quantity, 50)
        self.assertEqual(self.item.amount, 50)
        self.assertEqual(self.item.profit, Decimal("5.00"))
        self.assertEqual(self.item.total_cost, Decimal("500.00"))
        self.assertEqual(self.item.total_selling, Decimal("750.00"))
        self.assertEqual(self.item.total_profit, Decimal("250.00"))
        self.assertEqual(str(self.item), "Paracetamol 500mg")

    def test_batch_properties(self):
        self.assertEqual(self.batch1.name, "Paracetamol 500mg")
        self.assertEqual(self.batch1.amount, 20)
        self.assertEqual(self.batch1.cost_price, Decimal("10.00"))
        self.assertEqual(self.batch1.selling_price, Decimal("15.00"))
        self.assertEqual(self.batch1.profit, Decimal("5.00"))
        self.assertEqual(self.batch1.total_cost, Decimal("200.00"))
        self.assertEqual(self.batch1.total_selling, Decimal("300.00"))
        self.assertEqual(self.batch1.total_profit, Decimal("100.00"))
        self.assertIn("Paracetamol 500mg", str(self.batch1))


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.item = Item.objects.create(
            name="Amoxicillin 250mg",
            description="Antibiotic",
            cost_price=Decimal("20.00"),
            selling_price=Decimal("30.00"),
        )
        self.batch1 = Batch.objects.create(
            item=self.item,
            quantity=10,
            expiry_date=date.today() + timedelta(days=10),
        )
        self.batch2 = Batch.objects.create(
            item=self.item,
            quantity=15,
            expiry_date=date.today() + timedelta(days=50),
        )

    def test_inventory_view(self):
        response = self.client.get(reverse('inventory'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Amoxicillin 250mg")
        self.assertContains(response, "Total Cost Price")
        self.assertContains(response, "Total Selling Price")
        self.assertContains(response, "Total Profit")
        # 10*20 + 15*20 = 500.00
        self.assertEqual(response.context['total_cost_price'], "500.00")
        # 10*30 + 15*30 = 750.00
        self.assertEqual(response.context['total_selling_price'], "750.00")
        # 750 - 500 = 250.00
        self.assertEqual(response.context['total_profit'], "250.00")

    def test_new_item_view_get(self):
        response = self.client.get(reverse('new'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create New Item")

    def test_new_item_view_post_with_batch(self):
        post_data = {
            'name': 'Ibuprofen 400mg',
            'description': 'Anti-inflammatory',
            'cost_price': '5.00',
            'sale_price': '8.50',
            'quantity': '25',
            'expiry_date': (date.today() + timedelta(days=90)).isoformat(),
        }
        response = self.client.post(reverse('new'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        item = Item.objects.get(name='Ibuprofen 400mg')
        self.assertEqual(item.cost_price, Decimal('5.00'))
        self.assertEqual(item.selling_price, Decimal('8.50'))
        self.assertEqual(item.batches.count(), 1)
        batch = item.batches.first()
        self.assertEqual(batch.quantity, 25)
        self.assertEqual(batch.profit, Decimal('3.50'))

    def test_add_batch_view_get(self):
        response = self.client.get(reverse('add'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Amoxicillin 250mg")

    def test_add_batch_view_post(self):
        post_data = {
            'item_id': str(self.item.id),
            'quantity': '12',
            'expiry_date': (date.today() + timedelta(days=120)).isoformat(),
        }
        response = self.client.post(reverse('add'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.item.batches.count(), 3)
        self.assertEqual(self.item.total_quantity(), 10 + 15 + 12)

    def test_sell_view_get(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Amoxicillin 250mg")

    def test_sell_view_post_fefo_partial(self):
        # Total available: 25. Sell 5 -> should deduct from batch1 (earlier expiry)
        post_data = {
            'item_id': str(self.item.id),
            'quantity': '5',
        }
        response = self.client.post(reverse('home'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.batch1.refresh_from_db()
        self.batch2.refresh_from_db()
        self.assertEqual(self.batch1.quantity, 5)
        self.assertEqual(self.batch2.quantity, 15)
        self.assertEqual(self.item.total_quantity(), 20)

    def test_sell_view_post_fefo_across_batches(self):
        # Sell 15 -> batch1 (10) depleted to 0, batch2 (15) reduced to 10
        post_data = {
            'item_id': str(self.item.id),
            'quantity': '15',
        }
        response = self.client.post(reverse('home'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.batch1.refresh_from_db()
        self.batch2.refresh_from_db()
        self.assertEqual(self.batch1.quantity, 0)
        self.assertEqual(self.batch2.quantity, 10)
        self.assertEqual(self.item.total_quantity(), 10)

    def test_sell_view_post_insufficient_stock(self):
        # Total available: 25. Attempting to sell 30 should fail gracefully
        post_data = {
            'item_id': str(self.item.id),
            'quantity': '30',
        }
        response = self.client.post(reverse('home'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Insufficient stock")
        self.batch1.refresh_from_db()
        self.batch2.refresh_from_db()
        self.assertEqual(self.batch1.quantity, 10)
        self.assertEqual(self.batch2.quantity, 15)
