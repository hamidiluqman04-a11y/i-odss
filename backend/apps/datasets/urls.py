from django.urls import path

from . import views
from .models import AnalysisResult

Kind = AnalysisResult.Kind

urlpatterns = [
    path("", views.DatasetListView.as_view(), name="dataset-list"),
    path("<int:pk>/", views.DatasetDetailView.as_view(), name="dataset-detail"),
    path("<int:pk>/dashboard/", views.ResultView.as_view(kind=Kind.DASHBOARD), name="dataset-dashboard"),
    path("<int:pk>/inventory/", views.ResultView.as_view(kind=Kind.INVENTORY), name="dataset-inventory"),
    path("<int:pk>/forecast/", views.ResultView.as_view(kind=Kind.FORECAST), name="dataset-forecast"),
    path("<int:pk>/bundles/", views.ResultView.as_view(kind=Kind.BUNDLES), name="dataset-bundles"),
    path("<int:pk>/pricing/", views.ResultView.as_view(kind=Kind.PRICING), name="dataset-pricing"),
    path("<int:pk>/promo-simulation/", views.PromoSimulationView.as_view(), name="dataset-promo"),
]
