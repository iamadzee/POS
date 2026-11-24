from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from store.models import User, Item, Batch, Sale

class CustomUserAdmin(DefaultUserAdmin):
    list_display = ('username', 'email', 'is_admin', 'is_staff', 'is_superuser')
    list_filter = ('is_admin', 'is_staff', 'is_superuser')
    fieldsets = DefaultUserAdmin.fieldsets + (
        ('Store Role', {'fields': ('is_admin',)}),
    )


class BatchInline(admin.TabularInline):
    model = Batch
    extra = 1
    fields = ('quantity', 'expiry_date', 'is_archived')


class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'cost_price', 'selling_price', 'total_quantity_display', 'unexpired_quantity_display', 'profit_display', 'is_archived')
    list_filter = ('is_archived',)
    search_fields = ('name', 'description')
    inlines = [BatchInline]

    @admin.display(description="Active Stock")
    def total_quantity_display(self, obj):
        return obj.total_quantity()

    @admin.display(description="Sellable (Unexpired)")
    def unexpired_quantity_display(self, obj):
        return obj.unexpired_quantity()

    @admin.display(description="Unit Profit")
    def profit_display(self, obj):
        return f"{obj.profit:.2f}"


class BatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'quantity', 'expiry_date', 'cost_price_display', 'selling_price_display', 'profit_display', 'is_expired_display', 'is_archived')
    list_filter = ('is_archived', 'expiry_date', 'item')
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

    @admin.display(description="Expired?", boolean=True)
    def is_expired_display(self, obj):
        return obj.is_expired


class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'item_name', 'quantity', 'selling_price', 'total_price', 'profit')
    list_filter = ('timestamp', 'item')
    search_fields = ('item_name',)
    readonly_fields = ('timestamp',)


admin.site.register(User, CustomUserAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(Batch, BatchAdmin)
admin.site.register(Sale, SaleAdmin)
