from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Item, Batch

def home(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        quantity_to_sell = request.POST.get('quantity')

        if not item_id or not quantity_to_sell:
            messages.error(request, "Please select an item and enter a quantity to sell.")
            return redirect('home')

        try:
            quantity_to_sell = int(quantity_to_sell)
            if quantity_to_sell <= 0:
                messages.error(request, "Quantity to sell must be greater than zero.")
                return redirect('home')
        except ValueError:
            messages.error(request, "Please enter a valid quantity.")
            return redirect('home')

        item = get_object_or_404(Item, id=item_id)
        total_available = item.total_quantity()

        if quantity_to_sell > total_available:
            messages.error(
                request,
                f"Insufficient stock for '{item.name}'. Available: {total_available}, Requested: {quantity_to_sell}."
            )
            return redirect('home')

        # Sell using FEFO (First-Expired, First-Out)
        remaining = quantity_to_sell
        batches = item.batches.filter(quantity__gt=0).order_by('expiry_date')
        for batch in batches:
            if batch.quantity <= remaining:
                remaining -= batch.quantity
                batch.quantity = 0
                batch.save()
            else:
                batch.quantity -= remaining
                batch.save()
                remaining = 0
                break

        messages.success(request, f"Successfully sold {quantity_to_sell} unit(s) of '{item.name}'!")
        return redirect('home')

    items = Item.objects.all().prefetch_related('batches')
    return render(request, 'store/home.html', {'items': items})


def new(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        cost_price = request.POST.get('cost_price') or 0
        selling_price = request.POST.get('sale_price') or request.POST.get('selling_price') or 0
        quantity = request.POST.get('quantity')
        expiry_date = request.POST.get('expiry_date')

        if not name:
            messages.error(request, "Item name is required.")
            return redirect('new')

        item = Item.objects.create(
            name=name,
            description=description,
            cost_price=cost_price,
            selling_price=selling_price,
        )

        qty = 0
        if quantity:
            try:
                qty = int(quantity)
            except ValueError:
                qty = 0

        if expiry_date and qty > 0:
            Batch.objects.create(
                item=item,
                quantity=qty,
                expiry_date=expiry_date
            )

        messages.success(request, f"Item '{item.name}' created successfully!")
        return redirect('inventory')

    return render(request, 'store/new.html')


def add(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        quantity = request.POST.get('quantity')
        expiry_date = request.POST.get('expiry_date')

        if not item_id or not quantity or not expiry_date:
            messages.error(request, "Please fill in all required fields.")
            return redirect('add')

        try:
            qty = int(quantity)
            if qty <= 0:
                messages.error(request, "Batch quantity must be greater than zero.")
                return redirect('add')
        except ValueError:
            messages.error(request, "Please enter a valid batch quantity.")
            return redirect('add')

        item = get_object_or_404(Item, id=item_id)
        Batch.objects.create(
            item=item,
            quantity=qty,
            expiry_date=expiry_date
        )

        messages.success(request, f"Batch of {qty} added for '{item.name}'!")
        return redirect('inventory')

    items = Item.objects.all()
    return render(request, 'store/add.html', {'items': items})


def history(request):
    return render(request, 'store/history.html')


def inventory(request):
    batches = list(Batch.objects.select_related('item').all())

    # Include items that don't have any batch yet with quantity 0
    items_with_batches = {b.item_id for b in batches}
    unbatched_items = Item.objects.exclude(id__in=items_with_batches)

    class UnbatchedDisplay:
        def __init__(self, item):
            self.item = item
            self.name = item.name
            self.amount = 0
            self.quantity = 0
            self.cost_price = item.cost_price
            self.selling_price = item.selling_price
            self.profit = item.profit
            self.expiry_date = "No batches"
            self.total_cost = Decimal("0.00")
            self.total_selling = Decimal("0.00")
            self.total_profit = Decimal("0.00")

    display_batches = batches + [UnbatchedDisplay(item) for item in unbatched_items]

    total_cost_price = sum(b.cost_price * b.quantity for b in batches)
    total_selling_price = sum(b.selling_price * b.quantity for b in batches)
    total_profit = sum(b.profit * b.quantity for b in batches)

    context = {
        'batches': display_batches,
        'total_cost_price': f"{total_cost_price:.2f}",
        'total_selling_price': f"{total_selling_price:.2f}",
        'total_profit': f"{total_profit:.2f}",
    }
    return render(request, 'store/inventory.html', context)
