from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from store.models import User, Item, Batch, Sale

class ModelTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin_test",
            password="pass",
            is_admin=True,
            is_staff=True,
            is_superuser=True
        )
        self.clerk_user = User.objects.create_user(
            username="clerk_test",
            password="pass",
            is_admin=False,
            is_staff=False,
            is_superuser=False
        )
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
        self.expired_batch = Batch.objects.create(
            item=self.item,
            quantity=5,
            expiry_date=date.today() - timedelta(days=5),
        )

    def test_user_roles(self):
        self.assertTrue(self.admin_user.is_admin_user)
        self.assertFalse(self.admin_user.is_clerk_user)
        self.assertEqual(self.admin_user.role_display, "Admin")

        self.assertFalse(self.clerk_user.is_admin_user)
        self.assertTrue(self.clerk_user.is_clerk_user)
        self.assertEqual(self.clerk_user.role_display, "Clerk / Salesman")

    def test_item_properties(self):
        self.assertEqual(self.item.total_quantity(), 55)
        self.assertEqual(self.item.unexpired_quantity(), 50)
        self.assertEqual(self.item.expired_quantity(), 5)
        self.assertEqual(self.item.profit, Decimal("5.00"))

    def test_archiving_item_and_batch(self):
        # Archiving batch
        self.batch1.archive()
        self.assertTrue(self.batch1.is_archived)
        self.assertIsNotNone(self.batch1.archived_at)
        # Active quantity should now exclude batch1 (55 - 20 = 35)
        self.assertEqual(self.item.total_quantity(), 35)

        # Restoring batch
        self.batch1.restore()
        self.assertFalse(self.batch1.is_archived)
        self.assertEqual(self.item.total_quantity(), 55)

        # Archiving entire item
        self.item.archive()
        self.batch1.refresh_from_db()
        self.batch2.refresh_from_db()
        self.assertTrue(self.item.is_archived)
        self.assertTrue(self.batch1.is_archived)
        self.assertTrue(self.batch2.is_archived)

        # Restoring entire item
        self.item.restore()
        self.batch1.refresh_from_db()
        self.batch2.refresh_from_db()
        self.assertFalse(self.item.is_archived)
        self.assertFalse(self.batch1.is_archived)
        self.assertFalse(self.batch2.is_archived)


class RoleAndArchiveViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username="admin",
            password="admin123",
            is_admin=True,
            is_staff=True,
            is_superuser=True
        )
        self.clerk_user = User.objects.create_user(
            username="clerk",
            password="clerk123",
            is_admin=False,
            is_staff=False,
            is_superuser=False
        )
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

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_demo_login_buttons(self):
        # Demo login as clerk
        res = self.client.post(reverse('login'), {'demo_role': 'clerk'}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.context['user'].is_authenticated)
        self.assertTrue(res.context['user'].is_clerk_user)

        # Logout
        self.client.get(reverse('logout'), follow=True)

        # Demo login as admin
        res = self.client.post(reverse('login'), {'demo_role': 'admin'}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.context['user'].is_authenticated)
        self.assertTrue(res.context['user'].is_admin_user)

    def test_clerk_access_allowed_and_denied_views(self):
        self.client.login(username="clerk", password="clerk123")

        # Clerk CAN access home, inventory, history
        res = self.client.get(reverse('home'))
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('inventory'))
        self.assertEqual(res.status_code, 200)
        # Clerk should not see Cost Price column
        self.assertNotContains(res, "Sellable Cost Value")

        res = self.client.get(reverse('history'))
        self.assertEqual(res.status_code, 200)

        # Clerk is DENIED access to new, add, archives
        res = self.client.get(reverse('new'), follow=True)
        self.assertContains(res, "Access restricted: Administrator privileges required.")

        res = self.client.get(reverse('add'), follow=True)
        self.assertContains(res, "Access restricted: Administrator privileges required.")

        res = self.client.get(reverse('archives'), follow=True)
        self.assertContains(res, "Access restricted: Administrator privileges required.")

    def test_admin_has_full_access(self):
        self.client.login(username="admin", password="admin123")

        for url_name in ['home', 'new', 'add', 'inventory', 'history', 'archives']:
            res = self.client.get(reverse(url_name))
            self.assertEqual(res.status_code, 200)

    def test_admin_can_archive_and_restore_batch(self):
        self.client.login(username="admin", password="admin123")

        # Archive batch 1
        res = self.client.post(reverse('archive_batch', args=[self.batch1.id]), follow=True)
        self.assertEqual(res.status_code, 200)
        self.batch1.refresh_from_db()
        self.assertTrue(self.batch1.is_archived)

        # Archived batch should not appear in active inventory
        res = self.client.get(reverse('inventory'))
        self.assertNotContains(res, f"Batch #{self.batch1.id}")

        # Archived batch MUST appear in Archives Vault
        res = self.client.get(reverse('archives'))
        self.assertContains(res, f"#{self.batch1.id}")
        self.assertContains(res, "Amoxicillin 250mg")

        # Restore batch
        res = self.client.post(reverse('restore_batch', args=[self.batch1.id]), follow=True)
        self.assertEqual(res.status_code, 200)
        self.batch1.refresh_from_db()
        self.assertFalse(self.batch1.is_archived)

    def test_admin_can_archive_and_restore_item(self):
        self.client.login(username="admin", password="admin123")

        # Archive item
        res = self.client.post(reverse('archive_item', args=[self.item.id]), follow=True)
        self.assertEqual(res.status_code, 200)
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_archived)

        # Item should vanish from active inventory
        res = self.client.get(reverse('inventory'))
        self.assertNotContains(res, "Amoxicillin 250mg")

        # Item should vanish from Checkout search
        res = self.client.get(reverse('home'))
        self.assertNotContains(res, "Amoxicillin 250mg")

        # Item should be in Archives Vault
        res = self.client.get(reverse('archives'))
        self.assertContains(res, "Amoxicillin 250mg")

        # Restore item
        res = self.client.post(reverse('restore_item', args=[self.item.id]), follow=True)
        self.assertEqual(res.status_code, 200)
        self.item.refresh_from_db()
        self.assertFalse(self.item.is_archived)

        # Item is back in active inventory
        res = self.client.get(reverse('inventory'))
        self.assertContains(res, "Amoxicillin 250mg")

    def test_permanent_delete_removes_from_database(self):
        self.client.login(username="admin", password="admin123")

        # First archive
        self.item.archive()

        # Permanent delete
        res = self.client.post(reverse('delete_item_permanent', args=[self.item.id]), follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Item.objects.filter(id=self.item.id).exists())

    def test_clerk_cannot_archive_or_restore(self):
        self.client.login(username="clerk", password="clerk123")

        # Clerk attempts to archive
        res = self.client.post(reverse('archive_batch', args=[self.batch1.id]), follow=True)
        self.assertContains(res, "Access restricted: Administrator privileges required.")
        self.batch1.refresh_from_db()
        self.assertFalse(self.batch1.is_archived)

    def test_sell_and_history_logging(self):
        self.client.login(username="clerk", password="clerk123")

        # Clerk sells 5 units
        res = self.client.post(reverse('home'), {
            'item_id': str(self.item.id),
            'quantity': '5',
        }, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Sale.objects.count(), 1)
        sale = Sale.objects.first()
        self.assertEqual(sale.quantity, 5)
        self.assertEqual(sale.total_price, Decimal("150.00"))
