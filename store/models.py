from datetime import date
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    is_admin = models.BooleanField(default=False)

    @property
    def is_admin_user(self):
        return bool(self.is_admin or self.is_superuser or self.is_staff)

    @property
    def is_clerk_user(self):
        return not self.is_admin_user

    @property
    def role_display(self):
        return "Admin" if self.is_admin_user else "Clerk / Salesman"


class Item(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    cost_price = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    def total_quantity(self):
        return sum(batch.quantity for batch in self.batches.filter(is_archived=False))

    def unexpired_quantity(self):
        return sum(batch.quantity for batch in self.batches.filter(is_archived=False, expiry_date__gte=date.today()))

    def expired_quantity(self):
        return sum(batch.quantity for batch in self.batches.filter(is_archived=False, expiry_date__lt=date.today()))

    def archive(self):
        now = timezone.now()
        self.is_archived = True
        self.archived_at = now
        self.save()
        self.batches.filter(is_archived=False).update(is_archived=True, archived_at=now)

    def restore(self):
        self.is_archived = False
        self.archived_at = None
        self.save()
        self.batches.update(is_archived=False, archived_at=None)

    @property
    def quantity(self):
        return self.total_quantity()

    @property
    def amount(self):
        return self.total_quantity()

    @property
    def profit(self):
        return self.selling_price - self.cost_price

    @property
    def total_cost(self):
        return self.cost_price * self.total_quantity()

    @property
    def total_selling(self):
        return self.selling_price * self.total_quantity()

    @property
    def total_profit(self):
        return self.profit * self.total_quantity()


class Batch(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="batches")
    quantity = models.IntegerField()
    expiry_date = models.DateField()
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["expiry_date"]

    def __str__(self):
        return f"{self.item.name} - Exp: {self.expiry_date} ({self.quantity})"

    def archive(self):
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save()

    def restore(self):
        self.is_archived = False
        self.archived_at = None
        self.save()
        if self.item.is_archived:
            self.item.is_archived = False
            self.item.archived_at = None
            self.item.save()

    @property
    def name(self):
        return self.item.name if self.item else ""

    @property
    def amount(self):
        return self.quantity

    @amount.setter
    def amount(self, value):
        self.quantity = value

    @property
    def is_expired(self):
        return self.expiry_date < date.today()

    @property
    def cost_price(self):
        return self.item.cost_price if self.item else Decimal("0.00")

    @property
    def selling_price(self):
        return self.item.selling_price if self.item else Decimal("0.00")

    @property
    def profit(self):
        if self.item:
            return self.selling_price - self.cost_price
        return Decimal("0.00")

    @property
    def total_cost(self):
        return self.cost_price * self.quantity

    @property
    def total_selling(self):
        return self.selling_price * self.quantity

    @property
    def total_profit(self):
        return self.profit * self.quantity


class Sale(models.Model):
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True, related_name="sales")
    item_name = models.CharField(max_length=100)
    quantity = models.IntegerField()
    cost_price = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    total_price = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    profit = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.item_name} x {self.quantity} ({self.total_price})"
