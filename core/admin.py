from django.contrib import admin
from .models import Supplier, Product, Order, OrderItem


admin.site.site_header = "Wholesale Admin"
admin.site.site_title = "Wholesale Admin Portal"  
admin.site.index_title = "Welcome to the Wholesale Admin Portal"


 

# Register your models here.
admin.site.register(Supplier)
admin.site.register(Product)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer_name', 'status', 'total_price', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('buyer_name', 'buyer_email')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price')
    list_filter = ('order__created_at',)
