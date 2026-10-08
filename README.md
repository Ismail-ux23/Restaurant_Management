# Restaurant Ordering & Management System

A Django-based restaurant platform: customers browse the menu, order for
dine-in/takeaway/delivery, and track order status; staff manage the menu,
tables, inventory, and the live order queue; admins get full oversight via
the built-in Django admin site plus a sales dashboard.

Built on Django's ORM, auth system, and admin site rather than reinventing
them — this is meant to demonstrate real Django patterns, not just CRUD
forms wired to a database.

## What makes this more than basic CRUD

- **Automatic inventory deduction.** Menu items can be linked to the
  ingredients they consume (`MenuItemIngredient`). When staff confirm an
  order, stock is deducted atomically across every ingredient needed — and
  if anything would go negative, the *entire* confirmation is rejected
  with a clear message, with zero partial changes (wrapped in a DB
  transaction with ingredient and order row locks on PostgreSQL).
  Status changes reload the persisted order, so duplicate confirmations
  cannot apply the same deduction again.
- **A real order state machine.** Orders can only move
  `pending → confirmed → preparing → ready → completed`, or to `cancelled`
  from any non-terminal state. Skipping stages is rejected at the model
  level, not just hidden in the UI.
- **Inventory is restored on cancellation.** If a confirmed order gets
  cancelled, the quantities recorded in its deduction logs are returned automatically,
  even if the recipe or order lines were edited afterwards.
- **Table lifecycle.** Booking a dine-in order occupies the table;
  completing or cancelling the order frees it again.
- **Coupon validation.** Codes are checked for active status, date range,
  and usage limits before the discount is applied — not just looked up.
- **Full audit trail.** Every order status change and every inventory
  change (deduction, return, restock, manual adjustment) is logged with
  who did it and when — same pattern as the audit logs in the Inventory
  Management and Appointment Booking projects.
- **Reviews are gated.** A customer can only review a menu item they've
  actually received in a *completed* order, and only once per item.

## Roles

- **Customer** — signs up normally at `/accounts/signup/`. Browses the
  menu, orders, tracks status, leaves reviews.
- **Staff** — has `is_staff=True`. Gets the staff dashboard, order queue,
  menu/inventory/table management. Staff accounts are **not** self-signup
  — create them from the Django admin (this mirrors how real restaurant
  staff accounts are provisioned by a manager, not by employees signing
  themselves up).
- **Admin** — `is_superuser=True`. Gets everything staff has, plus the
  full Django admin site at `/admin/` for direct data management,
  user/staff management, and every model.

## Project Structure

```
restaurant_management/
├── manage.py
├── requirements.txt
├── .env.example
├── config/            # settings, root urls
├── accounts/          # Profile model, signup/login, staff_required decorator
├── menu/              # Category, MenuItem
├── inventory/         # InventoryItem, MenuItemIngredient, InventoryLog
├── tables/             # Table
├── orders/             # Cart, Order, OrderItem, Payment, Coupon, Review,
│                       # OrderStatusLog, and services.py (the business logic)
├── dashboard/          # staff home + sales report
├── templates/           # base.html
└── static/css/
```

---

## Running this project in Visual Studio Code

### 1. Prerequisites

- [Visual Studio Code](https://code.visualstudio.com/)
- [Python 3.12+](https://www.python.org/downloads/), on PATH
- VS Code's **Python extension** (by Microsoft)

### 2. Open the project

Unzip `restaurant_management`, then **File → Open Folder...** in VS Code.

### 3. Create a virtual environment

Terminal in VS Code (`` Ctrl+` ``):

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

If prompted "Select this environment for the workspace?", click **Yes**.

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Database setup

**Option A — quick start, no Postgres needed:** skip straight to step 6.
Without a `.env` file (or without `POSTGRES_HOST` set in it), the app
automatically uses a local SQLite file — no database server required.

**Option B — PostgreSQL:**
1. Install PostgreSQL locally, or use a hosted instance.
2. Create a database:
   ```sql
   CREATE DATABASE restaurant_management;
   ```
3. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
4. Fill in your Postgres credentials in `.env`:
   ```
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=restaurant_management
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your-actual-password
   SECRET_KEY=some-long-random-string
   ```
5. `.env` is in `.gitignore` — it won't be committed.

### 6. Migrate and create an admin account

```bash
python manage.py migrate
python manage.py createsuperuser
```
Follow the prompts (username, email, password). This account can log into
both `/admin/` and the staff dashboard.

### 7. Run the server

```bash
python manage.py runserver
```
Open `http://127.0.0.1:8000`.

### 8. First-time use

1. **As your superuser**, go to `http://127.0.0.1:8000/admin/`:
   - Add a **Category** (e.g. "Burgers") and a **MenuItem** (e.g.
     "Cheeseburger", price, mark available) — or use the regular staff UI
     at `/menu/staff/items/` and `/menu/staff/categories/` instead, same
     result.
   - Add a **Table** at `/tables/`.
   - *(Optional but recommended)* Add an **InventoryItem** (e.g. "Beef
     Patty", stock quantity, unit) at `/inventory/`, then link it to your
     menu item at `/inventory/recipes/` so stock deduction has something
     to do.
   - *(Optional)* Add a **Coupon** in the admin (`/admin/orders/coupon/`)
     with an active date range to test discounts at checkout.
2. **Create a staff account**: in `/admin/auth/user/`, add a new user and
   check **"Staff status"** (not superuser, unless you want them to also
   have full admin access). Log in as them at `/accounts/login/` to see
   the staff dashboard and order queue.
3. **Sign up as a customer** at `/accounts/signup/` (in a different
   browser/incognito window, or log out first). Browse the menu, add to
   cart, check out as dine-in/takeaway/delivery.
4. **Back as staff**, go to **Order Queue** and move the order through
   `Confirmed → Preparing → Ready → Completed`. Watch the linked inventory
   item's stock drop when you confirm it.
5. **Back as the customer**, once the order is completed, you can leave a
   review on that menu item from the order detail page.

### Stopping the server

`Ctrl+C` in the terminal.

---

## Notes before deploying anywhere public

- Set a real, random `SECRET_KEY` via `.env`.
- Set `DEBUG=false` in `.env`.
- Set `ALLOWED_HOSTS` in `.env` to your real domain.
- Run `python manage.py collectstatic` for production static file serving.
- Use a real WSGI server (gunicorn, uwsgi) instead of `runserver`.

## Deliberately left out of this build (noted in the original brief as "impressive extras")

These need external services/API keys, which this build intentionally
avoids so it runs standalone:

- Stripe/payment gateway integration (payments are recorded as
  cash/card with a staff "mark as paid" action instead)
- Real email delivery (order confirmations print to the console via
  Django's console email backend — swap `EMAIL_BACKEND` in `settings.py`
  for a real SMTP backend when you're ready)
- QR-code table ordering
- Real-time order status (would need WebSockets/Django Channels)
- PDF invoice generation
- REST API layer (Django REST Framework) — mentioned as a possible
  follow-up; the whole app currently works through server-rendered views

## Possible next steps

- Add Django REST Framework on top of the existing models for a mobile
  client or JS frontend
- WebSocket-based live order status updates for the kitchen display
- Stripe Checkout integration for real card payments
- PDF invoice generation with the `reportlab` or `weasyprint` library

## Order lifecycle checks

```bash
python manage.py test
python manage.py makemigrations --check --dry-run
```

GitHub Actions runs on Python 3.12 with SQLite and PostgreSQL 16. Regression
tests cover stale status requests, recipe changes after confirmation, returns
from recorded deductions, shortages, failed audit writes and the normal lifecycle.
The simultaneous-confirmation test runs on PostgreSQL; SQLite skips that test
because it does not implement `select_for_update` row locks. SQLite can still
raise database-lock errors under contention; it is intended for local use.

The status service locks the order before validating its current state and locks
ingredients in primary-key order. Conditional writes and audit logs are part of
the same transaction. No schema migration is required for these fixes. Returns
depend on retained inventory logs; deleting an inventory item deletes its logs.
Concurrent checkout/table reservation and coupon usage-counter accounting are
separate behavior and are not covered by these lifecycle fixes.
