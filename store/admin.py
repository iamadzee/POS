from django.contrib import admin
from store.models import Item, Batch

class BatchInline(admin.TabularInline):
    model = Batch
    extra = 1
    fields = ('quantity', 'expiry_date')

class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'cost_price', 'selling_price', 'total_quantity_display', 'profit_display')
    search_fields = ('name', 'description')
    inlines = [BatchInline]

    @admin.display(description="Total Quantity")
    def total_quantity_display(self, obj):
        return obj.total_quantity()

    @admin.display(description="Unit Profit")
    def profit_display(self, obj):
        return f"{obj.profit:.2f}"

class BatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'quantity', 'expiry_date', 'cost_price_display', 'selling_price_display', 'profit_display')
    list_filter = ('expiry_date', 'item')
    search_fields = ('item__name',)

    @admin.display(description="Cost Price")
    def cost_price_display(self, obj):
        return f"{obj.cost_price:.2f}"

    @admin.display(description="Selling Price")
    def selling_price_display(self, obj):
        return f"{obj.selling_price:.2f}"

    @admin.display(description="Unit Profit")
    def profit_display(self, obj):
        return f"{obj.profit:.2f}"

admin.site.register(Item, ItemAdmin)
admin.site.register(Batch, BatchAdmin)
