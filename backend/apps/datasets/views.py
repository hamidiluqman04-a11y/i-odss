"""
Dataset endpoints. Every endpoint requires login, and users only ever see
their own datasets (someone else's dataset id gives 404, as if it did not exist).

Upload flow (privacy decision D1):
  1. The CSV arrives in memory (settings.FILE_UPLOAD_HANDLERS) — never on disk.
  2. It is validated and analysed while in memory.
  3. Only the dataset summary and the aggregated results are saved.
  4. The file contents and the clean rows are then discarded.
"""
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.services.pipeline import run_analysis
from apps.analytics.services.pricing import simulate_promo_from
from config.exceptions import error_response

from .csv_parser import CSVValidationError, parse_csv
from .models import AnalysisResult, Dataset
from .serializers import DatasetSerializer, PromoSerializer, UploadSerializer

MAX_WARNINGS_RETURNED = 10


def own_dataset(request, pk):
    return get_object_or_404(Dataset, pk=pk, owner=request.user)


class DatasetListView(APIView):
    def get(self, request):
        datasets = Dataset.objects.filter(owner=request.user)
        return Response({"datasets": DatasetSerializer(datasets, many=True).data})

    def post(self, request):
        # Check the size before reading the body, so large files are refused clearly.
        if int(request.META.get("CONTENT_LENGTH") or 0) > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
            limit_mb = settings.FILE_UPLOAD_MAX_MEMORY_SIZE // (1024 * 1024)
            return error_response(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large",
                f"The file is too large. The maximum size is {limit_mb} MB.",
            )

        form = UploadSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        upload = form.validated_data["file"]
        try:
            parsed = parse_csv(upload.name, upload.read())
        except CSVValidationError as exc:
            extra = {"detected_headers": exc.detected_headers} if exc.detected_headers else {}
            return error_response(
                status.HTTP_422_UNPROCESSABLE_ENTITY, exc.error_type, exc.message, exc.errors, **extra
            )
        finally:
            upload.close()

        margin = form.validated_data["margin"]
        lead_times = form.validated_data["lead_times"]
        results = run_analysis(parsed.rows, margin=margin, lead_times=lead_times)

        with transaction.atomic():
            dataset = Dataset.objects.create(
                owner=request.user,
                original_filename=parsed.filename[:255],
                row_count=len(parsed.rows),
                skipped_row_count=parsed.skipped_row_count,
                sku_count=parsed.sku_count,
                date_start=parsed.date_start,
                date_end=parsed.date_end,
                column_mapping=parsed.column_mapping,
                analysis_settings={"margin": margin, "lead_times": lead_times},
            )
            AnalysisResult.objects.bulk_create(
                AnalysisResult(dataset=dataset, kind=kind, data=data) for kind, data in results.items()
            )

        return Response(
            {
                "dataset": DatasetSerializer(dataset).data,
                "warnings": parsed.warnings[:MAX_WARNINGS_RETURNED],
                "warning_count": len(parsed.warnings),
            },
            status=status.HTTP_201_CREATED,
        )


class DatasetDetailView(APIView):
    def get(self, request, pk):
        return Response({"dataset": DatasetSerializer(own_dataset(request, pk)).data})

    def delete(self, request, pk):
        own_dataset(request, pk).delete()   # its results are deleted with it
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResultView(APIView):
    """Returns one saved analysis (dashboard, inventory, forecast, bundles or pricing)."""

    kind = None

    def get(self, request, pk):
        dataset = own_dataset(request, pk)
        result = get_object_or_404(AnalysisResult, dataset=dataset, kind=self.kind)
        return Response({"dataset_id": dataset.id, self.kind: result.data})


class PromoSimulationView(APIView):
    def post(self, request, pk):
        dataset = own_dataset(request, pk)
        form = PromoSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        inputs = get_object_or_404(AnalysisResult, dataset=dataset, kind=AnalysisResult.Kind.PROMO_INPUTS).data
        sku = form.validated_data["sku"]
        if sku not in inputs:
            return error_response(
                status.HTTP_404_NOT_FOUND, "sku_not_found", f"SKU '{sku}' is not in this dataset."
            )
        margin = form.validated_data.get("margin", dataset.analysis_settings.get("margin"))
        discount = form.validated_data["discount_pct"]
        discount = int(discount) if discount.is_integer() else discount   # "10%", not "10.0%"
        result = simulate_promo_from(sku, inputs[sku], discount, margin)
        return Response({"dataset_id": dataset.id, "simulation": result})
