from django.contrib import admin

from .models import AnalysisResult, Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "owner", "row_count", "sku_count", "date_start", "date_end", "created_at")
    list_filter = ("owner",)


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ("dataset", "kind", "created_at")
    list_filter = ("kind",)
