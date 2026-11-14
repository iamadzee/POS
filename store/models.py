from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    pass

class Item(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    cost_price = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(default=0, max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name

    def total_quantity(self):
        return sum(batch.quantity for batch in self.batches.all())

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

    class Meta:
        ordering = ["expiry_date"]

    def __str__(self):
        return f"{self.item.name} - Exp: {self.expiry_date} ({self.quantity})"

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
