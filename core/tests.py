from django.test import TestCase
from django.urls import reverse
from .models import Order, Supplier, Product, OrderItem
from django.contrib.auth.models import User


class BuyerPagesTests(TestCase):
    def setUp(self):
        # create two orders by two buyers
        Order.objects.create(buyer_name="Alice", buyer_email="alice@example.com", buyer_phone="123", status='completed')
        Order.objects.create(buyer_name="Bob", buyer_email="bob@example.com", buyer_phone="456", status='completed')

    def test_buyer_list_page(self):
        # ensure authenticated user can view buyer list
        from django.contrib.auth.models import User
        user = User.objects.create_user('buyer', 'b@example.com', 'pw')
        self.client.login(username='buyer', password='pw')
        url = reverse('buyer_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alice")
        self.assertContains(response, "Bob")
        # link should escape the @ character (encoded in path)
        self.assertContains(response, "/buyers/alice%40example.com/")

    def test_buyer_detail_page(self):
        # not logged in -> redirected
        url = reverse('buyer_detail', args=["alice@example.com"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])
        # login and try again
        from django.contrib.auth.models import User
        user = User.objects.create_user('buyer', 'b@example.com', 'pw')
        self.client.login(username='buyer', password='pw')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "alice@example.com")
        self.assertContains(response, "Alice")
        self.assertNotContains(response, "Bob")

    def test_buyer_list_requires_login(self):
        url = reverse('buyer_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])
        # after login should succeed
        from django.contrib.auth.models import User
        user = User.objects.create_user('buyer2', 'b2@example.com', 'pw')
        self.client.login(username='buyer2', password='pw')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alice")
        self.assertContains(response, "Bob")

    def test_checkout_requires_login(self):
        """Anonymous users should be redirected when hitting checkout."""
        url = reverse('checkout')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_cart_requires_login(self):
        url = reverse('cart')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_logged_in_user_can_access_checkout(self):
        # create a simple user and log in
        from django.contrib.auth.models import User
        user = User.objects.create_user('testuser', 'test@example.com', 'secret')
        self.client.login(username='testuser', password='secret')
        url = reverse('checkout')
        response = self.client.get(url)
        # since cart is empty, checkout view redirects to product list
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(reverse('login'), response['Location'])

    def test_seller_dashboard_requires_seller_group(self):
        from django.contrib.auth.models import User, Group
        # create normal user
        user = User.objects.create_user('normal', 'n@example.com', 'pw')
        self.client.login(username='normal', password='pw')
        response = self.client.get(reverse('seller_dashboard'))
        self.assertEqual(response.status_code, 403)
        # now add to seller group
        seller_group, _ = Group.objects.get_or_create(name='seller')
        user.groups.add(seller_group)
        response = self.client.get(reverse('seller_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_seller_dashboard_redirects_anonymous_to_login(self):
        response = self.client.get(reverse('seller_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])


class CartCheckoutTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user('shopper', 'shopper@example.com', 'pw')
        self.supplier = Supplier.objects.create(name='ACME Supplies', contact_email='acme@example.com')
        self.product = Product.objects.create(
            name='Industrial Gloves',
            description='Safety gloves',
            price='10.00',
            supplier=self.supplier,
            stock=5
        )

    def test_add_to_cart_rejects_invalid_quantity(self):
        self.client.login(username='shopper', password='pw')
        response = self.client.post(
            reverse('add_to_cart', args=[self.product.id]),
            data={'quantity': 0}
        )
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {'success': False, 'message': 'Quantity must be greater than 0.'})

    def test_add_to_cart_rejects_quantity_over_stock(self):
        self.client.login(username='shopper', password='pw')
        response = self.client.post(
            reverse('add_to_cart', args=[self.product.id]),
            data={'quantity': 10}
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload['success'])
        self.assertEqual(payload['message'], 'Insufficient stock')

    def test_checkout_creates_order_and_updates_stock(self):
        self.client.login(username='shopper', password='pw')
        session = self.client.session
        session['cart'] = {str(self.product.id): 2}
        session.save()

        response = self.client.post(reverse('checkout'), data={
            'buyer_name': 'Shopper One',
            'buyer_email': 'shopper@example.com',
            'buyer_phone': '1234567890',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'order_success.html')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(str(order.total_price), '20.00')

    def test_checkout_rejects_invalid_email(self):
        self.client.login(username='shopper', password='pw')
        session = self.client.session
        session['cart'] = {str(self.product.id): 1}
        session.save()

        response = self.client.post(reverse('checkout'), data={
            'buyer_name': 'Shopper One',
            'buyer_email': 'not-an-email',
            'buyer_phone': '1234567890',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a valid email address.')
        self.assertEqual(Order.objects.count(), 0)


class SignupTests(TestCase):
    def test_signup_page_loads(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create account')

    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(reverse('signup'), data={
            'username': 'newuser',
            'account_type': 'user',
            'password1': 'StrongPass123!X',
            'password2': 'StrongPass123!X',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))
        self.assertTrue(User.objects.filter(username='newuser').exists())
        user = User.objects.get(username='newuser')
        self.assertFalse(user.groups.filter(name='seller').exists())
        # authenticated user should be redirected away from signup page
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))

    def test_signup_as_seller_adds_seller_group(self):
        response = self.client.post(reverse('signup'), data={
            'username': 'selleruser',
            'account_type': 'seller',
            'password1': 'StrongPass123!Y',
            'password2': 'StrongPass123!Y',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))
        user = User.objects.get(username='selleruser')
        self.assertTrue(user.groups.filter(name='seller').exists())
