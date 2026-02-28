# Wholeseller Django App

This is a basic wholeseller web application built with Django. It uses a Supabase PostgreSQL database.

## Setup

1. **Create a Supabase project**
   - Go to https://supabase.com and create a new project.
   - Navigate to `Settings > Database` and copy the `Connection string` (PostgreSQL). It looks like:
     ```
     postgres://user:password@db.host.supabase.co:5432/database
     ```

2. **Configure environment variables**
   - In the project root, create a file named `.env` and add:
     ```env
     DATABASE_URL="postgres://user:password@db.host.supabase.co:5432/database"
     DJANGO_SECRET_KEY="<your-secret-key>"
     SUPABASE_URL="https://your-project.supabase.co"
     SUPABASE_KEY="<anon-or-service-role-key>"
     ```
   - You can generate a secret key with `from django.core.management.utils import get_random_secret_key` in a Python shell.

3. **Install dependencies**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Apply migrations and create admin user**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Run development server**
   ```bash
   python manage.py runserver
   ```
   Visit http://127.0.0.1:8000/ to see the product list.

## Development

- The `core` app contains models for `Supplier` and `Product`.
- Admin interface available at `/admin`.

### Using Supabase client

If you prefer to bypass Django ORM for certain operations, use the `supabase` Python client:

```python
from supabase import create_client
import os

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')

supabase = create_client(url, key)

# example: fetch rows from a table
data = supabase.table('products').select('*').execute()
```

Set `SUPABASE_URL` and `SUPABASE_KEY` from your project settings.

## Buyers Page

A new buyers section allows you to explore customers who have made purchases. Navigate to `/buyers/` from the main menu or directly in the browser. Each buyer entry links to the detailed order history (requires admin login for order management).

### Authentication

Customers must be logged in before they can add items to the cart or proceed to checkout. Buyer pages (`/buyers/` and individual details) also require authentication. Use the **Login** link in the navigation bar to sign in; registrations must be created via the Django admin or another user‑management workflow.

Sellers have a dashboard protected by group membership. To access seller features, create a user and add them to the `seller` group (via the admin). Sellers use the normal login page (`/login/`) and then visit `/seller/dashboard/` for product management. A dashboard link appears in the navigation bar once a seller is authenticated.

## Notes

- Ensure the `DATABASE_URL` environment variable is set to connect to Supabase.
- SSL is required on Supabase connections; the Django settings enforce `ssl_require=True`.
