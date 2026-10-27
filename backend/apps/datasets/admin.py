from django.contrib import admin

from .models import Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "owner", "row_count", "sku_count", "date_start", "date_end", "created_at")
    list_filter = ("owner",)
