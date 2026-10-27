from django.conf import settings
from django.db import models


class Dataset(models.Model):
    """
    Metadata about one uploaded CSV file.

    Privacy (approved decision D1): the raw transaction rows are analysed in
    memory and then discarded. Only this summary is saved — no order IDs,
    no individual rows, no customer or region-per-order data.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="datasets"
    )
    original_filename = models.CharField(max_length=255)
    row_count = models.PositiveIntegerField(help_text="Valid rows used in the analysis.")
    skipped_row_count = models.PositiveIntegerField(
        default=0, help_text="Rows rejected by validation."
    )
    sku_count = models.PositiveIntegerField()
    date_start = models.DateField()
    date_end = models.DateField()
    column_mapping = models.JSONField(
        default=dict, help_text="Which CSV header was used for each field, e.g. {'qty': 'Quantity'}."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.row_count} rows)"
