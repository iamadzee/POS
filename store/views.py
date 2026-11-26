from datetime import date
from decimal import Decimal
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import User, Item, Batch, Sale

def admin_required(view_func):
    """Decorator ensuring that only Admin users can access the view."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Please log in to continue.")
            return redirect('login')
        if not request.user.is_admin_user:
            messages.error(request, "Access restricted: Administrator privileges required.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    # Seed demo users if they don't exist
    if not User.objects.filter(username='admin').exists():
        admin_u = User.objects.create_user(username='admin', password='admin123', is_admin=True, is_staff=True, is_superuser=True)
    if not User.objects.filter(username='clerk').exists():
        clerk_u = User.objects.create_user(username='clerk', password='clerk123', is_admin=False, is_staff=False, is_superuser=False)

    if request.method == 'POST':
        demo_role = request.POST.get('demo_role')
        if demo_role == 'admin':
            user = authenticate(request, username='admin', password='admin123')
            if user:
                login(request, user)
                messages.success(request, f"Logged in as Administrator ({user.username}).")
                return redirect('home')
        elif demo_role == 'clerk':
            user = authenticate(request, username='clerk', password='clerk123')
            if user:
                login(request, user)
                messages.success(request, f"Logged in as Clerk / Salesman ({user.username}).")
                return redirect('home')

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            role_label = "Administrator" if user.is_admin_user else "Clerk / Salesman"
            messages.success(request, f"Welcome back, {user.username}! Logged in as {role_label}.")
            next_url = request.GET.get('next')
            return redirect(next_url if next_url else 'home')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'store/login.html')


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


@login_required
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

        item = get_object_or_404(Item, id=item_id, is_archived=False)
        today = date.today()

        # Filter unexpired active batches with stock
        valid_batches = item.batches.filter(is_archived=False, quantity__gt=0, expiry_date__gte=today).order_by('expiry_date')
        unexpired_quantity = sum(batch.quantity for batch in valid_batches)

        # Check for expired active batches
        expired_batches = item.batches.filter(is_archived=False, quantity__gt=0, expiry_date__lt=today)
        expired_quantity = sum(batch.quantity for batch in expired_batches)

        if quantity_to_sell > unexpired_quantity:
            if expired_quantity > 0:
                messages.error(
                    request,
                    f"Blocked sale: '{item.name}' has {expired_quantity} expired unit(s) skipped. "
                    f"Only {unexpired_quantity} unexpired unit(s) available in stock (requested {quantity_to_sell})."
                )
            else:
                messages.error(
                    request,
                    f"Insufficient stock for '{item.name}'. Available: {unexpired_quantity}, Requested: {quantity_to_sell}."
                )
            return redirect('home')

        # Sell using FEFO (First-Expired, First-Out) from valid unexpired batches only
        remaining = quantity_to_sell
        for batch in valid_batches:
            if batch.quantity <= remaining:
                remaining -= batch.quantity
                batch.quantity = 0
                batch.save()
            else:
                batch.quantity -= remaining
                batch.save()
                remaining = 0
                break

        # Log sale in History
        total_price = item.selling_price * quantity_to_sell
        profit = (item.selling_price - item.cost_price) * quantity_to_sell
        Sale.objects.create(
            item=item,
            item_name=item.name,
            quantity=quantity_to_sell,
            cost_price=item.cost_price,
            selling_price=item.selling_price,
            total_price=total_price,
            profit=profit
        )

        msg = f"Successfully sold {quantity_to_sell} unit(s) of '{item.name}' for {total_price:.2f}!"
        if expired_quantity > 0:
            msg += f" Note: {expired_quantity} expired unit(s) remain on shelf and should be disposed."

        messages.success(request, msg)
        return redirect('home')

    items = Item.objects.filter(is_archived=False).prefetch_related('batches')
    return render(request, 'store/home.html', {'items': items})


@admin_required
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


@admin_required
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

        item = get_object_or_404(Item, id=item_id, is_archived=False)
        Batch.objects.create(
            item=item,
            quantity=qty,
            expiry_date=expiry_date
        )

        messages.success(request, f"Batch of {qty} added for '{item.name}'!")
        return redirect('inventory')

    items = Item.objects.filter(is_archived=False)
    return render(request, 'store/add.html', {'items': items})


@login_required
def history(request):
    sales = Sale.objects.all().order_by('-timestamp')
    today = timezone.localdate()

    today_sales = [s for s in sales if timezone.localtime(s.timestamp).date() == today]
    today_cash_total = sum(s.total_price for s in today_sales)
    today_profit = sum(s.profit for s in today_sales)
    today_sales_count = len(today_sales)
    today_items_sold = sum(s.quantity for s in today_sales)

    all_time_cash = sum(s.total_price for s in sales)
    all_time_profit = sum(s.profit for s in sales)

    context = {
        'sales': sales,
        'today_cash_total': f"{today_cash_total:.2f}",
        'today_profit': f"{today_profit:.2f}",
        'today_sales_count': today_sales_count,
        'today_items_sold': today_items_sold,
        'all_time_cash': f"{all_time_cash:.2f}",
        'all_time_profit': f"{all_time_profit:.2f}",
    }
    return render(request, 'store/history.html', context)


@login_required
def inventory(request):
    # Only active, unarchived batches and items
    batches = list(
        Batch.objects.filter(is_archived=False, item__is_archived=False)
        .select_related('item')
        .all()
    )

    items_with_batches = {b.item_id for b in batches}
    unbatched_items = Item.objects.filter(is_archived=False).exclude(id__in=items_with_batches)

    class UnbatchedDisplay:
        def __init__(self, item):
            self.id = None
            self.item = item
            self.name = item.name
            self.amount = 0
            self.quantity = 0
            self.cost_price = item.cost_price
            self.selling_price = item.selling_price
            self.profit = item.profit
            self.expiry_date = "No batches"
            self.is_expired = False
            self.total_cost = Decimal("0.00")
            self.total_selling = Decimal("0.00")
            self.total_profit = Decimal("0.00")

    display_batches = batches + [UnbatchedDisplay(item) for item in unbatched_items]

    # Only count sellable (unexpired) stock towards expected revenue and profit
    sellable_batches = [b for b in batches if not b.is_expired]
    total_cost_price = sum(b.cost_price * b.quantity for b in sellable_batches)
    total_selling_price = sum(b.selling_price * b.quantity for b in sellable_batches)
    total_profit = sum(b.profit * b.quantity for b in sellable_batches)

    total_sellable_units = sum(b.quantity for b in sellable_batches)

    context = {
        'batches': display_batches,
        'total_cost_price': f"{total_cost_price:.2f}",
        'total_selling_price': f"{total_selling_price:.2f}",
        'total_profit': f"{total_profit:.2f}",
        'total_sellable_units': total_sellable_units,
    }
    return render(request, 'store/inventory.html', context)


# ==========================================
# ARCHIVES & DELETION VIEWS (ADMIN ONLY)
# ==========================================

@admin_required
def archive_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    item.archive()
    messages.success(request, f"'{item.name}' and all its batches have been moved to the Archives.")
    return redirect('inventory')


@admin_required
def archive_batch(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id)
    item_name = batch.item.name
    batch.archive()
    messages.success(request, f"Batch #{batch.id} of '{item_name}' (Qty: {batch.quantity}) moved to Archives.")
    return redirect('inventory')


@admin_required
def archives(request):
    archived_items = Item.objects.filter(is_archived=True).order_by('-archived_at')
    archived_batches = Batch.objects.filter(is_archived=True).select_related('item').order_by('-archived_at')

    context = {
        'archived_items': archived_items,
        'archived_batches': archived_batches,
        'archived_items_count': archived_items.count(),
        'archived_batches_count': archived_batches.count(),
    }
    return render(request, 'store/archives.html', context)


@admin_required
def restore_item(request, item_id):
    item = get_object_or_404(Item, id=item_id, is_archived=True)
    item.restore()
    messages.success(request, f"'{item.name}' and its batches have been restored to active inventory!")
    return redirect('archives')


@admin_required
def restore_batch(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id, is_archived=True)
    batch.restore()
    messages.success(request, f"Batch #{batch.id} of '{batch.item.name}' restored to active inventory!")
    return redirect('archives')


@admin_required
def delete_item_permanent(request, item_id):
    item = get_object_or_404(Item, id=item_id, is_archived=True)
    name = item.name
    item.delete()
    messages.success(request, f"'{name}' has been permanently deleted.")
    return redirect('archives')


@admin_required
def delete_batch_permanent(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id, is_archived=True)
    item_name = batch.item.name
    batch_id_num = batch.id
    batch.delete()
    messages.success(request, f"Batch #{batch_id_num} of '{item_name}' permanently deleted.")
    return redirect('archives')
