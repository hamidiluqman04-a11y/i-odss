import logging

from django.conf import settings
from django.db import connection
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)

# Lets start.ps1 tell this backend apart from other apps that answer /api/health/.
SERVICE_NAME = "I-ODSS"


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Report whether the API is running and can reach PostgreSQL."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        # Full details go to the server log only, never to the client.
        logger.exception("Health check: database unreachable")
        return Response(
            {"service": SERVICE_NAME, "status": "error", "database": "unavailable"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response({"service": SERVICE_NAME, "status": "ok", "database": "ok"})


def react_app(request):
    """
    Production only: return the built React app's index.html for page addresses
    such as /forecast, so React's router can show the right page (also after a refresh).
    In development there is no build, and the Vite dev server serves the pages instead.
    """
    index = settings.FRONTEND_DIST / "index.html"
    if not index.is_file():
        raise Http404("The React app has not been built.")
    response = FileResponse(index.open("rb"), content_type="text/html")
    response["Cache-Control"] = "no-cache"   # always fetch the latest build's page
    return response
