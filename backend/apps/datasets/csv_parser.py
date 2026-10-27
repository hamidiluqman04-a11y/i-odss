"""
Reads an uploaded CSV file and turns it into clean, validated rows.

Ported from legacy/backend/main.py (map_columns, parse_rows and the checks in
upload_csv). Behaviour is the same except for these deliberate fixes:

  1. Dates are stored as real dates (2025-01-15), whatever format the file
     used. The legacy app stored the original text, so "15/01/2025" crashed
     the forecast and sorted the date range wrongly.
  2. A product-name column is kept separately from the SKU code, so screens
     can show "Mechanical Keyboard" instead of "SKU-001".
  3. A "revenue" column is no longer mistaken for the unit price, and a
     "review" (text) column is no longer mistaken for the rating.
  4. Missing ratings / returns stay empty (None) instead of being invented
     (the legacy app silently used rating 4.5 and 0 returns).
  5. Quantities must be whole numbers ("2.5" used to become 2 silently) and
     prices must be finite ("inf" used to pass).
  6. Short rows no longer produce a product called "None".
  7. "skipped_row_count" counts skipped rows; the legacy "warning_count"
     counted error messages, so one bad row could count as several.
  8. An optional stock column is read, so inventory can use real stock
     levels instead of simulated ones.
"""
import csv
import io
import math
from dataclasses import dataclass, field
from datetime import datetime

# Internal field name -> header names we accept (case-insensitive).
# Covers Shopee / Lazada / TikTok Shop exports plus Malay / Indonesian names.
COLUMN_ALIASES = {
    "order_id":     ["orderid", "order_id", "order id", "ordernumber", "order_number",
                     "invoice", "invoice_id", "no pesanan", "id pesanan"],
    "sku":          ["sku", "sku_id", "item_sku", "product_sku", "sku code", "product id",
                     "product_id", "item_id", "sellersku", "seller_sku", "kod sku"],
    "product_name": ["productname", "product_name", "product name", "item name", "item_name",
                     "sku name", "nama produk", "product", "item"],
    "date":         ["date", "order_date", "created_at", "time", "timestamp",
                     "transaction_date", "order date", "waktu pesanan", "tarikh",
                     "tarikh pesanan", "created", "order_created"],
    "qty":          ["quantity", "qty", "units", "unit_sold", "quantity_sold",
                     "item_quantity", "jumlah", "kuantiti", "jumlah_item", "sold"],
    "price":        ["price", "unit_price", "item_price", "selling_price",
                     "harga", "harga asal", "unit price", "selling price", "unitprice",
                     "item price", "harga_unit"],
    "category":     ["category", "kategori", "product_category", "item_category",
                     "product category", "jenis", "jenis produk"],
    "region":       ["region", "location", "state", "negeri", "kawasan", "city",
                     "buyer_state", "shipping_state"],
    "rating":       ["rating", "score", "stars", "product_rating"],
    "returns":      ["returns", "return", "returned", "is_return", "refund"],
    "stock":        ["stock", "stock_on_hand", "stock on hand", "on_hand", "inventory",
                     "stock_qty", "available_stock", "stok"],
}

REQUIRED_FIELDS = ("sku", "date", "qty", "price")

REQUIRED_HINTS = {
    "sku":   "e.g. SKU, product_sku, ProductName, item_name, SellerSKU",
    "date":  "e.g. Date, order_date, created_at, waktu pesanan",
    "qty":   "e.g. Quantity, qty, units, jumlah",
    "price": "e.g. UnitPrice, price, selling_price, harga",
}

DATE_FORMATS = (
    "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y", "%d %b %Y",
    "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M:%S",
)

ENCODINGS = ("utf-8-sig", "utf-8", "latin-1", "cp1252")


class CSVValidationError(Exception):
    """The file cannot be analysed. Carries a message that is safe to show users."""

    def __init__(self, error_type, message, errors=None, detected_headers=None):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.errors = errors or []
        self.detected_headers = detected_headers


@dataclass
class ParsedCSV:
    filename: str
    rows: list
    column_mapping: dict          # internal field -> original header
    warnings: list = field(default_factory=list)
    skipped_row_count: int = 0

    @property
    def sku_count(self):
        return len({r["sku"] for r in self.rows})

    @property
    def date_start(self):
        return min(r["date"] for r in self.rows)

    @property
    def date_end(self):
        return max(r["date"] for r in self.rows)


def map_columns(headers):
    """
    Match the file's headers to our internal field names.
    Returns (mapping: internal field -> original header, missing required fields).
    """
    by_underscored = {h.strip().lower().replace(" ", "_"): h for h in headers}
    by_lower = {h.strip().lower(): h for h in headers}

    mapping = {}
    for internal, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            header = by_underscored.get(alias.replace(" ", "_")) or by_lower.get(alias)
            if header:
                mapping[internal] = header
                break

    # A file with only a product-name column still works: the name is the SKU.
    if "sku" not in mapping and "product_name" in mapping:
        mapping["sku"] = mapping["product_name"]

    missing = [f for f in REQUIRED_FIELDS if f not in mapping]
    return mapping, missing


def _cell(row, header):
    if not header:
        return ""
    return (row.get(header) or "").strip()


def _parse_date(text):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            continue
    return None


def _optional_number(text, cast):
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return cast(value) if math.isfinite(value) else None


def parse_rows(raw_rows, mapping):
    """
    Validate each row. Returns (clean_rows, error_messages, skipped_row_count).
    Bad rows are skipped; each problem is reported with its row number.
    """
    clean, errors, skipped = [], [], 0
    h = mapping.get

    for line_no, raw in enumerate(raw_rows, start=2):  # line 1 is the header
        row_errors = []

        sku = _cell(raw, h("sku"))
        if not sku:
            row_errors.append(f"Row {line_no}: '{h('sku')}' is empty")

        raw_date = _cell(raw, h("date"))
        order_date = None
        if not raw_date:
            row_errors.append(f"Row {line_no}: '{h('date')}' is empty")
        else:
            order_date = _parse_date(raw_date)
            if order_date is None:
                row_errors.append(
                    f"Row {line_no}: '{h('date')}' has unrecognised date format "
                    f"'{raw_date}' (expected YYYY-MM-DD)"
                )

        raw_qty = _cell(raw, h("qty"))
        qty = None
        try:
            qty_value = float(raw_qty)
            if not qty_value.is_integer():
                row_errors.append(f"Row {line_no}: '{h('qty')}' must be a whole number, got '{raw_qty}'")
            elif qty_value <= 0:
                row_errors.append(f"Row {line_no}: '{h('qty')}' must be a positive integer, got '{raw_qty}'")
            else:
                qty = int(qty_value)
        except ValueError:
            row_errors.append(f"Row {line_no}: '{h('qty')}' must be a number, got '{raw_qty}'")

        raw_price = _cell(raw, h("price"))
        price = None
        try:
            price_value = float(raw_price.replace(",", ""))
            if not math.isfinite(price_value) or price_value <= 0:
                row_errors.append(f"Row {line_no}: '{h('price')}' must be positive, got '{raw_price}'")
            else:
                price = price_value
        except ValueError:
            row_errors.append(f"Row {line_no}: '{h('price')}' must be a decimal number, got '{raw_price}'")

        if row_errors:
            errors.extend(row_errors)
            skipped += 1
            continue

        stock = None
        raw_stock = _cell(raw, h("stock"))
        if raw_stock:
            stock = _optional_number(raw_stock, int)
            if stock is None or stock < 0:
                errors.append(f"Row {line_no}: '{h('stock')}' value '{raw_stock}' ignored (not a whole number ≥ 0)")
                stock = None

        clean.append({
            "order_id": _cell(raw, h("order_id")) or f"ROW-{line_no}",
            "date":     order_date,
            "sku":      sku,
            "product":  _cell(raw, h("product_name")) or sku,
            "category": _cell(raw, h("category")) or "General",
            "qty":      qty,
            "price":    price,
            "region":   _cell(raw, h("region")) or "Unknown",
            "rating":   _optional_number(_cell(raw, h("rating")), float),
            "returns":  _optional_number(_cell(raw, h("returns")), int),
            "stock":    stock,
        })

    return clean, errors, skipped


def parse_csv(filename, content):
    """
    Decode, map and validate an uploaded CSV file (given as bytes).
    Raises CSVValidationError when the file cannot be used at all.
    """
    filename = filename or ""
    if not filename.lower().endswith(".csv"):
        raise CSVValidationError(
            "file_type_error", "Only CSV (.csv) files are accepted.", [f"Received: '{filename}'"]
        )

    for encoding in ENCODINGS:
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - latin-1 accepts any byte sequence
        raise CSVValidationError("encoding_error", "Cannot decode file. Save it as UTF-8 CSV and re-upload.")

    try:
        reader = csv.DictReader(io.StringIO(text))
        raw_rows = list(reader)
        headers = reader.fieldnames or []
    except csv.Error as exc:
        raise CSVValidationError("parse_error", f"Cannot parse CSV structure: {exc}")

    if not raw_rows:
        raise CSVValidationError("empty_file", "The CSV file is empty or contains only a header row.")

    mapping, missing = map_columns(list(headers))
    if missing:
        raise CSVValidationError(
            "missing_columns",
            f"Your CSV is missing {len(missing)} required column(s). I-ODSS accepts exports "
            f"from Shopee, Lazada, TikTok Shop, or any custom CSV with these data points.",
            [f"Cannot find column for '{f}' — accepted names: {REQUIRED_HINTS[f]}" for f in missing],
            detected_headers=list(headers)[:20],
        )

    rows, errors, skipped = parse_rows(raw_rows, mapping)
    if not rows:
        raise CSVValidationError(
            "no_valid_rows",
            "No valid rows found after validation. Fix the errors below and re-upload.",
            errors[:20],
        )

    return ParsedCSV(filename, rows, mapping, errors, skipped)
