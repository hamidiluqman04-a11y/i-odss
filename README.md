# I-ODSS v8 — Intelligent Operational Decision Support System
### CDCS230 Final Year Project | FastAPI + Vanilla JS

## Quick Start
```bash
# Windows: double-click run.bat
# Manual:
cd backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```
Open: http://localhost:8000

## Login
- seller@iodss.com / demo1234
- admin@iodss.com / admin123
- Or click "⚡ Quick Demo Access" to bypass login instantly

## What's New in v8

### 1. Dynamic Currency Selector (Feature 1)
Topbar dropdown: RM / Rp / ₱ / S$ / ฿ / $
All monetary values update instantly and persist in localStorage.

### 2. Quick Demo Access / Stateless Login (Feature 2)
Green one-click button on login page — no typing required for demo/testing.

### 3. Interactive 7-Step Tutorial (Feature 3)
"💡 Tutorial" topbar button — custom step-by-step guided walkthrough
covering upload → action cards → XAI → promo simulator → tools.
No external library required (pure JS, 7 steps with progress pills).

### 4. Session Analysis History (Feature 4)
"History" topbar button → right-side drawer listing every upload
this session with revenue, orders, SKU count, date range.
Backed by localStorage + new /api/session-summary endpoint.

### 5. PDF Report Export (Feature 5)
"📄 PDF" button appears after upload → downloads A4 PDF via html2pdf.js CDN.
Includes: KPI summary, inventory alerts, pricing recs, bundle pairs, forecast.
All values formatted in the selected currency.

## Carried Forward (v7)
- Flexible column mapper (Shopee/Lazada/TikTok Shop)
- Inline validation errors with collapsible panel
- Fast-Action / Deep-Verification single-scroll layout
- XAI plain_explain + technical xai on every endpoint
- Profitable/Margin-loss badges on Pricing, Bundles, Promo Sim
- FP-Growth with co-occurrence fallback
- RAM-only architecture

## Sample Files
- data_bundling_test.csv — BEST for demo (89% multi-item orders, FP-Growth)
- data_electronics.csv — 150 rows
- data_fashion.csv — 100 rows
- data_beauty.csv — 100 rows

## API Endpoints (v8)
POST /api/login
POST /api/upload
GET  /api/status
GET  /api/session-summary   ← NEW in v8
GET  /api/metrics
GET  /api/inventory
GET  /api/forecast
GET  /api/bundles
GET  /api/pricing
GET  /api/sales-trend
GET  /api/top-skus
GET  /api/category-breakdown
GET  /api/regional
GET  /api/sku-list
POST /api/simulate/promo
