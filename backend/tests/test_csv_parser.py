import datetime

import pytest

from apps.datasets.csv_parser import CSVValidationError, map_columns, parse_csv

HEADER = "OrderID,Date,SKU,Quantity,UnitPrice\n"


def parse_text(text, name="test.csv"):
    return parse_csv(name, text.encode("utf-8"))


def error_of(text, name="test.csv"):
    with pytest.raises(CSVValidationError) as exc:
        parse_text(text, name)
    return exc.value


# ── Same behaviour as the legacy app ──────────────────────────────────────

def test_rejects_non_csv_file():
    assert error_of("x", name="data.xlsx").error_type == "file_type_error"


def test_rejects_header_only_file():
    assert error_of(HEADER).error_type == "empty_file"


def test_reports_each_missing_required_column():
    err = error_of("OrderID,Date,Colour\nO1,2025-01-01,Red\n")
    assert err.error_type == "missing_columns"
    assert len(err.errors) == 3          # sku, qty, price
    assert err.detected_headers == ["OrderID", "Date", "Colour"]


def test_maps_malay_marketplace_headers():
    parsed = parse_text("no pesanan,tarikh,nama produk,kuantiti,harga\nO1,2025-01-01,Tee,2,49.0\n")
    assert parsed.column_mapping["sku"] == "nama produk"
    assert parsed.rows[0]["product"] == "Tee"


def test_header_matching_ignores_case_and_spaces():
    mapping, missing = map_columns([" ORDER DATE ", "Item_SKU", "QTY", "Selling Price"])
    assert missing == []
    assert mapping == {"date": " ORDER DATE ", "sku": "Item_SKU", "qty": "QTY", "price": "Selling Price"}


def test_skips_invalid_rows_and_reports_row_numbers():
    parsed = parse_text(
        HEADER + "O1,2025-01-01,A,2,10\nO2,not-a-date,A,1,10\nO3,2025-01-02,A,-1,10\nO4,2025-01-03,A,1,abc\n"
    )
    assert len(parsed.rows) == 1
    assert parsed.skipped_row_count == 3
    assert parsed.warnings[0].startswith("Row 3:")


def test_all_rows_invalid_raises():
    assert error_of(HEADER + "O1,2025-01-01,A,0,10\n").error_type == "no_valid_rows"


def test_accepts_latin1_encoded_file():
    content = "OrderID,Date,SKU,Quantity,UnitPrice\nO1,2025-01-01,Café Latte,1,10\n".encode("latin-1")
    assert parse_csv("x.csv", content).rows[0]["sku"] == "Café Latte"


def test_thousands_separator_in_price():
    assert parse_text(HEADER + 'O1,2025-01-01,A,1,"1,250.50"\n').rows[0]["price"] == 1250.5


def test_rows_without_order_id_become_separate_orders():
    parsed = parse_text("Date,SKU,Quantity,UnitPrice\n2025-01-01,A,1,10\n2025-01-01,B,1,10\n")
    assert [r["order_id"] for r in parsed.rows] == ["ROW-2", "ROW-3"]


# ── Deliberate fixes ──────────────────────────────────────────────────────

def test_day_first_dates_become_real_dates_with_correct_range():
    parsed = parse_text(HEADER + "O1,15/01/2025,A,1,10\nO2,03/02/2025,A,2,10\n")
    assert parsed.rows[0]["date"] == datetime.date(2025, 1, 15)
    assert (parsed.date_start, parsed.date_end) == (datetime.date(2025, 1, 15), datetime.date(2025, 2, 3))


def test_product_name_kept_separately_from_sku():
    parsed = parse_text("OrderID,Date,SKU,ProductName,Quantity,UnitPrice\nO1,2025-01-01,SKU-1,Webcam 1080p,1,215\n")
    assert parsed.rows[0]["sku"] == "SKU-1"
    assert parsed.rows[0]["product"] == "Webcam 1080p"


def test_revenue_column_is_not_used_as_price():
    err = error_of("OrderID,Date,SKU,Quantity,Revenue\nO1,2025-01-01,A,2,20\n")
    assert err.error_type == "missing_columns"
    assert "price" in err.errors[0]


def test_review_text_is_not_used_as_rating():
    parsed = parse_text("OrderID,Date,SKU,Quantity,UnitPrice,Review\nO1,2025-01-01,A,1,10,Great!\n")
    assert "rating" not in parsed.column_mapping
    assert parsed.rows[0]["rating"] is None


def test_missing_optional_values_stay_empty():
    row = parse_text(HEADER + "O1,2025-01-01,A,1,10\n").rows[0]
    assert row["rating"] is None
    assert row["returns"] is None
    assert row["stock"] is None
    assert (row["category"], row["region"]) == ("General", "Unknown")


def test_decimal_quantity_is_rejected():
    parsed = parse_text(HEADER + "O1,2025-01-01,A,2.5,10\nO2,2025-01-01,A,2.0,10\n")
    assert [r["qty"] for r in parsed.rows] == [2]
    assert "whole number" in parsed.warnings[0]


def test_infinite_price_is_rejected():
    parsed = parse_text(HEADER + "O1,2025-01-01,A,1,inf\nO2,2025-01-01,A,1,10\n")
    assert len(parsed.rows) == 1
    assert "must be positive" in parsed.warnings[0]


def test_short_row_does_not_create_product_named_none():
    parsed = parse_text(HEADER + "O1,2025-01-01\nO2,2025-01-01,A,1,10\n")
    assert [r["sku"] for r in parsed.rows] == ["A"]
    assert parsed.skipped_row_count == 1


def test_skipped_row_count_counts_rows_not_messages():
    parsed = parse_text(HEADER + "O1,bad-date,A,x,y\nO2,2025-01-01,A,1,10\n")
    assert len(parsed.warnings) == 3
    assert parsed.skipped_row_count == 1


def test_stock_column_is_read_and_bad_values_ignored():
    parsed = parse_text(
        "OrderID,Date,SKU,Quantity,UnitPrice,Stock\n"
        "O1,2025-01-01,A,1,10,25\nO2,2025-01-02,A,1,10,-3\nO3,2025-01-03,A,1,10,\n"
    )
    assert [r["stock"] for r in parsed.rows] == [25, None, None]
    assert len(parsed.rows) == 3                 # a bad stock value does not drop the sale
    assert "ignored" in parsed.warnings[0]


# ── Same results as legacy on the real sample files ───────────────────────

def test_samples_match_legacy_upload_summary(sample):
    parsed, legacy = sample
    up = legacy["upload"]
    assert len(parsed.rows) == up["rows"]
    assert parsed.sku_count == up["skus"]
    assert f"{parsed.date_start} to {parsed.date_end}" == up["date_range"]
    assert parsed.skipped_row_count == up["warning_count"] == 0
    # Same headers chosen; the only addition is the separate product name.
    assert {k: v for k, v in parsed.column_mapping.items() if k != "product_name"} == up["col_map"]
    assert parsed.column_mapping["product_name"] == "ProductName"
