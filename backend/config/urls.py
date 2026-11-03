from django.contrib import admin
from django.urls import include, path, re_path

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", views.health, name="health"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/datasets/", include("apps.datasets.urls")),
    # Every other address (/, /forecast, /pricing, ...) belongs to the React app.
    re_path(r"^(?!api/|admin/|static/).*$", views.react_app, name="react-app"),
]
