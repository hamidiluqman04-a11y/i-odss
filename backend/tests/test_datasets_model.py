import datetime

import pytest
from django.contrib.auth import get_user_model

from apps.datasets.models import Dataset


def make_dataset(owner, name="sales.csv", **extra):
    fields = dict(
        owner=owner, original_filename=name, row_count=150, sku_count=8,
        date_start=datetime.date(2025, 1, 3), date_end=datetime.date(2025, 3, 19),
        column_mapping={"qty": "Quantity"},
    )
    fields.update(extra)
    return Dataset.objects.create(**fields)


@pytest.fixture
def seller(db):
    return get_user_model().objects.create_user("seller@example.com", password="a-strong-test-pass-123")


def test_password_is_stored_hashed(seller):
    assert seller.password != "a-strong-test-pass-123"
    assert seller.check_password("a-strong-test-pass-123")


def test_create_and_read_back(seller):
    ds = make_dataset(seller)
    saved = Dataset.objects.get(pk=ds.pk)
    assert saved.owner == seller
    assert saved.skipped_row_count == 0
    assert saved.column_mapping == {"qty": "Quantity"}
    assert str(saved) == "sales.csv (150 rows)"


def test_newest_first(seller):
    make_dataset(seller, "old.csv")
    make_dataset(seller, "new.csv")
    assert [d.original_filename for d in Dataset.objects.all()] == ["new.csv", "old.csv"]


def test_update_and_delete(seller):
    ds = make_dataset(seller)
    ds.skipped_row_count = 3
    ds.save()
    assert Dataset.objects.get(pk=ds.pk).skipped_row_count == 3
    ds.delete()
    assert not Dataset.objects.exists()


def test_deleting_user_deletes_their_datasets(seller):
    make_dataset(seller)
    seller.delete()
    assert not Dataset.objects.exists()


def test_model_has_no_raw_transaction_fields():
    # Privacy guard: if someone adds row-level fields later, this test fails.
    names = {f.name for f in Dataset._meta.get_fields()}
    assert not names & {"rows", "raw_data", "order_id", "order_ids", "transactions", "file"}
