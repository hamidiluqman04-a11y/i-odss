# I-ODSS — Intelligent Operational Decision Support System

CDCS230 Final Year Project · **Django + Django REST Framework + React + PostgreSQL**

I-ODSS helps small e-commerce sellers make decisions from their own sales exports
(Shopee, Lazada, TikTok Shop or any CSV). Upload a file and it shows:

| Feature | What the seller gets | Method |
|---|---|---|
| **Dashboard** | Revenue, orders, average order value, weekly sales, best sellers, category and region totals | Aggregation of the uploaded rows |
| **Demand forecast** | Expected units for each of the next 4 weeks, with a likely range and a *measured* accuracy | SARIMA(1,1,1)(1,1,0)[7] on daily sales (statsmodels); 4-week moving average when history is short |
| **Product bundles** | Products often bought together, a suggested bundle price and its break-even | FP-Growth + association rules (mlxtend) |
| **Pricing** | How sales reacted to price changes, and a cautious 5% price-test suggestion | Price elasticity of demand (PED) from a weekly log-log regression |
| **Promotion simulator** | What a discount does to weekly profit, and the exact break-even sales increase | Constant-elasticity projection + margin maths |
| **Inventory** | Reorder point per product and, if the file has stock levels, what to restock | Reorder point = daily demand × lead time + safety stock |

Every result comes with a plain-language explanation for sellers and a technical
explanation for examiners. **I-ODSS never invents numbers:** when the data cannot
support an answer (e.g. prices never changed, no stock column, too few weeks), the
page says so and explains what data is needed.

---

## 1. Quick start (Windows PowerShell)

**You need:** Python 3.13, Node.js 20 or newer, PostgreSQL 14 or newer (tested with 18), Git.

### First-time setup

From the project folder:

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python -m pip install -r backend\requirements.txt
```

```bash
copy backend\.env.example backend\.env
```

Open `backend\.env` in an editor and fill in:

- `DJANGO_SECRET_KEY` — any long random text. Generate one with
  `.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(50))"`
- `DB_PASSWORD` — a new password for the app's database user (letters, digits, `-`, `_`)
- `DEMO_USER_PASSWORD` — the password for the demo login

Then, from the `backend` folder, create the database (asks for your PostgreSQL
**postgres** admin password), create the tables, and create the demo account:

```bash
powershell -ExecutionPolicy Bypass -File scripts\setup_db.ps1
```

```bash
..\.venv\Scripts\python manage.py migrate
```

```bash
..\.venv\Scripts\python manage.py create_demo_user
```

Install the frontend once, from the `frontend` folder:

```bash
npm install
```

### Every time you work on it — two terminals

Terminal 1, in `backend`:

```bash
..\.venv\Scripts\python manage.py runserver
```

Terminal 2, in `frontend`:

```bash
npm run dev
```

Open **http://localhost:5173** and log in with `DEMO_USER_EMAIL` / `DEMO_USER_PASSWORD`
from `backend\.env`, or create your own account. Try the files under
*Upload data → Demo data* (they are made-up sample data, not real sales).

Stop either server with **Ctrl+C**.

---

## 2. Running the tests

| Suite | Where | Command | What it covers |
|---|---|---|---|
| Backend | `backend` | `..\.venv\Scripts\python -m pytest` | Algorithms, CSV validation, API, login, privacy, end-to-end workflow (215 tests, ~1.5 min) |
| Frontend | `frontend` | `npm test` | API client, pages, forms, error states (45 tests) |
| Live smoke test | `backend` | `..\.venv\Scripts\python scripts\smoke_test.py` | A running server, checked from outside (16 checks) |
| Legacy baseline | project root | `.venv\Scripts\python -m pytest legacy\tests` | The original prototype's recorded outputs (20 tests) |

The backend tests create their own temporary database, so your data is not touched.
For the smoke test, start the backend first; add `http://localhost:5173` as an
argument to test through the React dev server instead.

---

## 3. How it works

```
 Browser (React, port 5173)
    │  /api/... requests (Vite forwards them in development)
    ▼
 Django REST Framework (port 8000)
    ├── apps/accounts   login, register, logout (session cookie + CSRF)
    ├── apps/datasets   CSV upload → validation → analysis → save results
    └── apps/analytics  pure-Python algorithms (no web code):
          services/kpis.py, inventory.py, forecasting.py,
          bundling.py, pricing.py, pipeline.py (runs them all)
    │
    ▼
 PostgreSQL   users · dataset summaries · analysis results (no raw rows)
```

**Upload flow:** the CSV is read **in memory** → headers are matched (many
marketplace and Malay/Indonesian names) → every row is validated (bad rows are
skipped and reported with their row number) → all analyses run → only the dataset
summary and the aggregated results are saved → the file contents are discarded.
The pages then read the saved results.

### Project structure

```
iodss/
├── backend/
│   ├── config/            settings (read from .env), URLs, error format, health check
│   ├── apps/accounts/     login/register API, create_demo_user command
│   ├── apps/datasets/     models, CSV parser, upload & results API
│   ├── apps/analytics/    services/ — the algorithms
│   ├── scripts/           setup_db.ps1, smoke_test.py
│   ├── tests/             pytest suites + fixtures (sample CSVs, legacy outputs)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/pages/         Dashboard, Forecast, Bundles, Pricing, Inventory, Upload, Login
│   ├── src/components/    layout, cards, states (loading / empty / error)
│   ├── src/charts/        Recharts charts
│   ├── src/hooks/         login state, datasets, results, currency
│   ├── src/services/      api.js (the only file that calls the backend), formatting
│   └── public/samples/    demo CSV files
├── legacy/                the original FastAPI prototype, kept for comparison
├── DESIGN.md              the UI design system (Wise-inspired; all colours, type and spacing come from here)
├── CLAUDE.md              rules for AI coding assistants (always follow DESIGN.md)
└── README.md
```

---

## 4. Privacy model

- Uploaded files are processed **in memory only** (never written to disk; 10 MB limit).
- The database stores: user accounts (passwords **hashed** by Django), dataset
  summaries (file name, row/product counts, date range, column mapping), and
  **aggregated** results (per week, per product, per pair, per category/region).
- It never stores individual orders, order IDs or raw rows. A test checks that no
  order ID from an uploaded file reaches the database.
- Users only see their own datasets. Deleting a dataset deletes its results.
- Secrets live in `backend\.env`, which Git ignores. The React app contains no secrets.
- **Trade-off:** to re-run an analysis with a different margin, upload the file again.

---

## 5. CSV format

| | Fields | Accepted header examples |
|---|---|---|
| **Required** | date, SKU *or* product name, quantity, unit price | `Date`, `order_date`, `tarikh` · `SKU`, `SellerSKU`, `ProductName` · `Quantity`, `qty`, `kuantiti` · `UnitPrice`, `price`, `harga` |
| Recommended | order ID (needed for bundles), product name, category | `OrderID`, `no pesanan` · `ProductName` · `Category`, `kategori` |
| Optional | region, rating, returns, **stock on hand** (enables restock alerts) | `Region`, `negeri` · `Rating` · `Returns` · `Stock`, `stok` |

Comma-, semicolon- and tab-separated files are accepted (in semicolon files `10,50`
means 10.50). Dates such as `2025-01-15`, `15/01/2025`, `15-01-2025` and
`2025-01-15 13:45:00` are recognised.

---

## 6. API reference

All endpoints are under `/api/`. Everything except health, CSRF, login and register
requires login. Errors always look like
`{"error": {"type": "...", "message": "...", "details": ...}}`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health/` | Server and database status |
| GET | `/api/auth/csrf/` | Sets the CSRF cookie (call first) |
| POST | `/api/auth/login/` · `/api/auth/register/` · `/api/auth/logout/` | Session login (rate-limited: 10 logins/min, 5 sign-ups/hour per IP) |
| GET | `/api/auth/me/` | Current user |
| GET / POST | `/api/datasets/` | List datasets / upload a CSV (`file`, optional `margin`, `lead_times`) |
| GET / DELETE | `/api/datasets/{id}/` | Dataset summary / delete it and its results |
| GET | `/api/datasets/{id}/dashboard/` · `forecast/` · `bundles/` · `pricing/` · `inventory/` | Saved results |
| POST | `/api/datasets/{id}/promo-simulation/` | `{"sku", "discount_pct", "margin"?}` |

Status codes: 400 invalid input · 401 wrong login · 403 not logged in / missing CSRF
token · 404 not found or not yours · 413 file too large · 422 file cannot be analysed ·
429 too many attempts · 503 database unavailable.

---

## 7. Changes from the original prototype

The original FastAPI app is kept in `legacy/` (run `legacy\run.bat`). The audit
found several results that were not what they claimed; these were fixed on purpose:

| Prototype | Now |
|---|---|
| "SARIMA" was a trend line plus a sine wave; MAPE was always 4.2% | Real SARIMA; accuracy measured on held-back weeks and compared with a simple average |
| PED came from fixed category numbers | PED estimated from the seller's own price changes, with confidence range; no PED when prices never changed |
| "Co-occurrence fallback" invented bundles when no order had two products | Honest "not enough multi-product orders" message |
| Stock was simulated as 8% of units sold | Real stock from the file, or "stock unknown" |
| Lift inflated, profit badges without evidence | Correct support/confidence/lift; break-even figures instead of "profitable" badges |
| Promo profit formula was wrong | Corrected (tested against hand calculations) |
| `15/01/2025` dates crashed the forecast; product names were lost | Fixed |
| Plain-text passwords, unprotected API, shared global data | Hashed passwords, login required, per-user data |

### Not carried over yet

These prototype features are **not** in the new app yet:

- **Interactive tutorial** (7-step walkthrough)
- **PDF report export**
- **Session analysis history.** This is partly replaced by the saved dataset list on
  the Upload page and the dataset picker.

The "Quick Demo Access" button was removed on purpose: it skipped login entirely.

---

## 8. Known limitations

- The sample files have fixed prices, no stock column and 7–11 weeks of history, so
  they cannot show measured PED, restock alerts or (on most files) forecast accuracy.
- Forecasts cover all products together; per-product forecasts are not offered yet.
- Supplier lead times use category defaults; the upload API accepts overrides but the
  upload page does not offer them yet.
- PED from sales history shows association, not proof of cause (promotions or seasons
  can coincide with price changes). The app says this in its explanations.
- Rate-limit counters are kept in memory, which is fine for a single development
  server but not for a multi-server deployment.
- The setup is for local development (`DJANGO_DEBUG=True`, Vite dev server).
  Production deployment is not covered.

---

## 9. Working safely with Git

- See what changed: `git status`, then `git diff` (or `git diff --staged`).
- Undo uncommitted changes to one file: `git restore path\to\file`.
- Go back to the original prototype at any time: `git switch updated`.
- Never commit `backend\.env` or real sales files (`.gitignore` blocks them).
