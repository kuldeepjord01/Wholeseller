from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from decimal import Decimal, InvalidOperation
from functools import wraps
from .models import Product, Supplier, Order, OrderItem

# Create your views here.

def home(request):
    return render(request, 'home.html')


def signup(request):
    if request.user.is_authenticated:
        return redirect('home')

    account_type = 'user'
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        account_type = request.POST.get('account_type', 'user')
        if form.is_valid():
            user = form.save()
            if account_type == 'supplier':
                supplier_group, _ = Group.objects.get_or_create(name='supplier')
                user.groups.add(supplier_group)
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()

    return render(request, 'signup.html', {'form': form, 'account_type': account_type})


def product_list(request):
    products = Product.objects.all()
    return render(request, 'product_list.html', {'products': products})


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'product_detail.html', {'product': product})


def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'supplier_list.html', {'suppliers': suppliers})


def _parse_positive_int(raw_value, default=1):
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _build_cart_snapshot(cart_items):
    products_in_cart = []
    total_price = Decimal('0')
    normalized_cart = {}

    for product_id, raw_quantity in cart_items.items():
        quantity = _parse_positive_int(raw_quantity, default=0)
        if quantity <= 0:
            continue
        try:
            product = Product.objects.get(id=int(product_id))
        except (Product.DoesNotExist, ValueError, TypeError):
            continue

        capped_quantity = min(quantity, max(product.stock, 0))
        if capped_quantity <= 0:
            continue

        subtotal = product.price * capped_quantity
        normalized_cart[str(product.id)] = capped_quantity
        products_in_cart.append({
            'product': product,
            'quantity': capped_quantity,
            'subtotal': subtotal,
        })
        total_price += subtotal

    return products_in_cart, total_price, normalized_cart


@login_required

def cart(request):
    """Display shopping cart"""
    cart_items = request.session.get('cart', {})
    products_in_cart, total_price, normalized_cart = _build_cart_snapshot(cart_items)
    if normalized_cart != cart_items:
        request.session['cart'] = normalized_cart
        request.session.modified = True

    return render(request, 'cart.html', {
        'cart_items': products_in_cart,
        'total_price': total_price,
        'cart_count': sum(normalized_cart.values()) if normalized_cart else 0
    })


@require_POST
@login_required

def add_to_cart(request, product_id):
    """Add product to cart (AJAX)"""
    product = get_object_or_404(Product, id=product_id)
    quantity = _parse_positive_int(request.POST.get('quantity'), default=0)

    if quantity <= 0:
        return JsonResponse({'success': False, 'message': 'Quantity must be greater than 0.'}, status=400)

    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    current_quantity = _parse_positive_int(cart.get(product_id_str), default=0)
    new_quantity = current_quantity + quantity

    if product.stock < new_quantity:
        return JsonResponse({'success': False, 'message': 'Insufficient stock'}, status=400)

    cart[product_id_str] = new_quantity
    request.session['cart'] = cart
    request.session.modified = True

    cart_count = sum(cart.values())
    return JsonResponse({
        'success': True,
        'message': f'{product.name} added to cart!',
        'cart_count': cart_count
    })


@require_POST
@login_required

def remove_from_cart(request, product_id):
    """Remove product from cart"""
    cart = request.session.get('cart', {})
    if str(product_id) in cart:
        del cart[str(product_id)]
        request.session['cart'] = cart
        request.session.modified = True
    
    return redirect('cart')


@require_POST
@login_required

def update_cart(request, product_id):
    """Update product quantity in cart"""
    quantity = _parse_positive_int(request.POST.get('quantity'), default=0)
    cart = request.session.get('cart', {})

    if quantity > 0:
        try:
            product = Product.objects.get(id=product_id)
            cart[str(product_id)] = min(quantity, max(product.stock, 0))
        except Product.DoesNotExist:
            pass
    else:
        if str(product_id) in cart:
            del cart[str(product_id)]

    if cart.get(str(product_id)) == 0:
        del cart[str(product_id)]

    request.session['cart'] = cart
    request.session.modified = True

    return redirect('cart')


@login_required

def buyer_list(request):
    """Display list of unique buyers based on orders."""
    # gather distinct buyers from orders
    buyers = Order.objects.values('buyer_name', 'buyer_email', 'buyer_phone').distinct()
    return render(request, 'buyer_list.html', {'buyers': buyers})


# seller utilities
def seller_required(view_func):
    """Decorator that ensures the user is logged in and belongs to seller group."""
    from django.http import HttpResponseForbidden

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.groups.filter(name='seller').exists():
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden('You must be a seller to access this page.')
    return _wrapped


@seller_required
def seller_dashboard(request):
    """Simple seller dashboard listing all products."""
    products = Product.objects.all()
    return render(request, 'seller_dashboard.html', {'products': products})


@login_required

def buyer_detail(request, email):
    """Show orders placed by a specific buyer identified by email."""
    orders = Order.objects.filter(buyer_email=email).order_by('-created_at')
    return render(request, 'buyer_detail.html', {'orders': orders, 'buyer_email': email})


@login_required

def checkout(request):
    """Checkout page"""
    cart_items = request.session.get('cart', {})

    products_in_cart, total_price, normalized_cart = _build_cart_snapshot(cart_items)
    if normalized_cart != cart_items:
        request.session['cart'] = normalized_cart
        request.session.modified = True
    if not products_in_cart:
        return redirect('product_list')

    if request.method == 'POST':
        buyer_name = (request.POST.get('buyer_name') or '').strip()
        buyer_email = (request.POST.get('buyer_email') or '').strip().lower()
        buyer_phone = (request.POST.get('buyer_phone') or '').strip()

        if not buyer_name:
            return render(request, 'checkout.html', {
                'products': products_in_cart,
                'total_price': total_price,
                'error': 'Buyer name is required.'
            })

        try:
            validate_email(buyer_email)
        except ValidationError:
            return render(request, 'checkout.html', {
                'products': products_in_cart,
                'total_price': total_price,
                'error': 'Please enter a valid email address.'
            })

        try:
            with transaction.atomic():
                cart_product_ids = [item['product'].id for item in products_in_cart]
                products = Product.objects.select_for_update().filter(id__in=cart_product_ids)
                products_by_id = {product.id: product for product in products}

                for item in products_in_cart:
                    current_product = products_by_id.get(item['product'].id)
                    if current_product is None:
                        return render(request, 'checkout.html', {
                            'products': products_in_cart,
                            'total_price': total_price,
                            'error': 'One or more products are no longer available.'
                        })
                    if current_product.stock < item['quantity']:
                        return render(request, 'checkout.html', {
                            'products': products_in_cart,
                            'total_price': total_price,
                            'error': f'Insufficient stock for {current_product.name}'
                        })

                order = Order.objects.create(
                    buyer_name=buyer_name,
                    buyer_email=buyer_email,
                    buyer_phone=buyer_phone,
                    status='completed'
                )

                order_items = []
                for item in products_in_cart:
                    current_product = products_by_id[item['product'].id]
                    order_items.append(
                        OrderItem(
                            order=order,
                            product=current_product,
                            quantity=item['quantity'],
                            price=current_product.price,
                        )
                    )
                    current_product.stock -= item['quantity']
                    current_product.save(update_fields=['stock'])

                OrderItem.objects.bulk_create(order_items)
                order.calculate_total()
        except (InvalidOperation, ValueError):
            return render(request, 'checkout.html', {
                'products': products_in_cart,
                'total_price': total_price,
                'error': 'Checkout failed due to invalid cart data.'
            })

        request.session['cart'] = {}
        request.session.modified = True

        return render(request, 'order_success.html', {
            'order': order,
        })

    return render(request, 'checkout.html', {
        'products': products_in_cart,
        'total_price': total_price
    })
