from django.db import models
from django.utils import timezone

# Basic wholeseller models

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='products')
    stock = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    buyer_name = models.CharField(max_length=255)
    buyer_email = models.EmailField()
    buyer_phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.buyer_name}"
    
    def calculate_total(self):
        """Calculate total price from order items"""
        total = sum(item.get_subtotal() for item in self.items.all())
        self.total_price = total
        self.save()
        return total


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at time of purchase

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def get_subtotal(self):
        """Calculate subtotal for this item"""
        return self.price * self.quantity
