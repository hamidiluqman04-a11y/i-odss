# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary: small e-commerce sellers** in Malaysia and Southeast Asia who sell on Shopee, Lazada, TikTok Shop or their own store. They are not data scientists or accountants. They export a CSV of their orders, upload it, and want to know what to do next: how much stock to order, which products to sell together, whether to change a price, whether a promotion will pay off.
- **Secondary: the project's supervisor and examiners.** I-ODSS is a CDCS230 final-year university project. Examiners read the technical explanations, the methods (SARIMA, FP-Growth, PED, reorder point) and the measured accuracy to judge whether the analysis is sound and honestly reported.

## Product Purpose

I-ODSS (Intelligent Operational Decision Support System) turns a seller's own sales export into operational decisions: a demand forecast, product bundle suggestions, price-sensitivity insight with a promotion simulator, and reorder points with restock alerts, plus an overview dashboard. Success means a seller understands each result well enough to act on it, and an examiner can verify that every number comes from a real method applied to the uploaded data.

## Positioning

Honest, explained advice. Every result is produced by a real algorithm run on the seller's own data, explained in plain language next to the technical method, and never invented. When the data cannot support an answer (prices never changed, no stock column, too few weeks, too few multi-product orders), I-ODSS says so and explains what data would be needed, instead of guessing. Uploaded files are analysed in memory and discarded; only aggregated results are stored.

## Operating Context

- Workflow: export orders from a marketplace as CSV → upload → review dashboard, forecast, bundles, pricing and inventory → act (restock, bundle, test a price, run a promotion).
- Accepted files: comma-, semicolon- or tab-separated CSV with flexible headers (English, Malay and Indonesian marketplace names). Required: date, SKU or product name, quantity, unit price. Optional: order ID, category, region, rating, returns, stock on hand.
- Money is shown with a selectable currency symbol (RM default; Rp, ₱, S$, ฿, $). The symbol is a label only; amounts are never converted.
- Each user has an account and sees only their own datasets.

## Capabilities and Constraints

- Forecast: SARIMA(1,1,1)(1,1,0)[7] on daily sales for the next 4 weeks with a 90% range; accuracy (MAPE/MAE) measured on held-back weeks against a simple-average baseline; a labelled moving average when history is short.
- Bundles: FP-Growth pairs with support, confidence, lift, a suggested bundle price and a break-even uplift at an assumed margin.
- Pricing: price elasticity estimated per product only when its price actually varied; advice limited to a small price test chosen by estimated profit; promotion simulator with exact break-even.
- Inventory: reorder point from daily demand, category lead-time defaults and safety stock; restock status only when the file contains stock levels.
- Privacy: raw rows and order IDs are never stored. Re-running with different assumptions means uploading the file again.
- Not yet built: the prototype's interactive tutorial and PDF report export; per-product forecasts; editing lead times in the UI.

## Brand Commitments

- Name: **I-ODSS**.
- Voice: plain, calm, non-technical English for sellers, with technical detail available on request for examiners. Recommendations are framed as estimates to test, never guarantees ("Treat this as a guide for planning, not a guarantee").

## Evidence on Hand

- Four made-up demo CSV files in `frontend/public/samples/` (beauty, bundling test, electronics, fashion). They are synthetic and must always be labelled as demo data.
- There are **no** real seller datasets, user-testing results, testimonials, customer counts, revenue outcomes or press. Future work must not invent any of these.

## Product Principles

1. **Never invent a number.** If the data cannot support a result, show the gap and what would fill it.
2. **Explain before advising.** Every result carries a plain-language meaning for sellers and a technical basis for examiners.
3. **Estimates, not promises.** Advice is a small, testable step with its assumptions (such as margin) visible and adjustable.
4. **The seller's data stays the seller's.** Process in memory, store only aggregates, show users only their own data.
5. **Respect a non-expert's time.** Lead with what to do next; keep methods one click away.
