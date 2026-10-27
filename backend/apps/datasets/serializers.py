from rest_framework import serializers

from apps.analytics.services.pricing import DEFAULT_MARGIN

from .models import Dataset


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = [
            "id", "original_filename", "row_count", "skipped_row_count", "sku_count",
            "date_start", "date_end", "column_mapping", "analysis_settings", "created_at",
        ]


class UploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    margin = serializers.FloatField(required=False, default=DEFAULT_MARGIN)
    # Sent as a JSON string in the form, e.g. '{"Skincare": 10}'.
    lead_times = serializers.JSONField(required=False, default=dict, binary=True)

    def validate_margin(self, value):
        if not 0 < value < 1:
            raise serializers.ValidationError("Margin must be between 0 and 1 (e.g. 0.4 for 40%).")
        return value

    def validate_lead_times(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('Use an object like {"Skincare": 10}.')
        for category, days in value.items():
            if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 365:
                raise serializers.ValidationError(
                    f"Lead time for '{category}' must be a whole number of days between 1 and 365."
                )
        return value


class PromoSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=255)
    discount_pct = serializers.FloatField(min_value=1, max_value=80)
    margin = serializers.FloatField(required=False)

    def validate_margin(self, value):
        if not 0 < value < 1:
            raise serializers.ValidationError("Margin must be between 0 and 1 (e.g. 0.4 for 40%).")
        return value
