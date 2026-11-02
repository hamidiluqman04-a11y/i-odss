from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", views.health, name="health"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/datasets/", include("apps.datasets.urls")),
]
