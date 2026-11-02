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
    analysis_settings = models.JSONField(
        default=dict, help_text="Assumptions used for this analysis, e.g. {'margin': 0.4, 'lead_times': {}}."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.row_count} rows)"


class AnalysisResult(models.Model):
    """
    One saved analysis output for a dataset (e.g. the forecast).

    These contain only aggregated numbers (per week, per product, per pair,
    per category/region) — never individual orders or transaction rows.
    """

    class Kind(models.TextChoices):
        DASHBOARD = "dashboard"
        INVENTORY = "inventory"
        FORECAST = "forecast"
        BUNDLES = "bundles"
        PRICING = "pricing"
        PROMO_INPUTS = "promo_inputs"

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="results")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["dataset", "kind"], name="one_result_per_kind")]

    def __str__(self):
        return f"{self.kind} for dataset {self.dataset_id}"
