from django.core.management.base import BaseCommand
from core.models import Supplier, Product


class Command(BaseCommand):
    help = 'Seed the database with sample suppliers and products'

    def handle(self, *args, **options):
        # Create suppliers
        suppliers_data = [
            {'name': 'ABC Wholesale Inc', 'contact_email': 'contact@abcwholesale.com'},
            {'name': 'Global Imports Ltd', 'contact_email': 'info@globalimports.com'},
            {'name': 'Direct Factory Sales', 'contact_email': 'sales@directfactory.com'},
        ]

        suppliers = {}
        for sup_data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(**sup_data)
            suppliers[sup_data['name']] = supplier
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created supplier: {supplier.name}'))

        # Create products
        products_data = [
            {
                'name': 'Laptop Computer',
                'description': 'High-performance laptop for professionals',
                'price': 899.99,
                'stock': 50,
                'supplier': suppliers['ABC Wholesale Inc'],
            },
            {
                'name': 'Office Chair',
                'description': 'Ergonomic office chair with lumbar support',
                'price': 299.99,
                'stock': 120,
                'supplier': suppliers['ABC Wholesale Inc'],
            },
            {
                'name': 'Desk Lamp',
                'description': 'LED desk lamp with adjustable brightness',
                'price': 49.99,
                'stock': 200,
                'supplier': suppliers['Global Imports Ltd'],
            },
            {
                'name': 'Keyboard and Mouse Set',
                'description': 'Wireless keyboard and mouse combo',
                'price': 79.99,
                'stock': 150,
                'supplier': suppliers['Global Imports Ltd'],
            },
            {
                'name': 'Monitor Stand',
                'description': 'Adjustable monitor stand for desk organization',
                'price': 45.00,
                'stock': 100,
                'supplier': suppliers['Direct Factory Sales'],
            },
            {
                'name': 'USB Hub',
                'description': '7-port USB 3.0 hub with power adapter',
                'price': 39.99,
                'stock': 250,
                'supplier': suppliers['Direct Factory Sales'],
            },
        ]

        for prod_data in products_data:
            product, created = Product.objects.get_or_create(
                name=prod_data['name'],
                defaults=prod_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created product: {product.name}'))

        self.stdout.write(self.style.SUCCESS('Database seeding completed!'))
