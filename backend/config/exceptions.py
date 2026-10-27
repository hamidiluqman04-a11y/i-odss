"""
One error format for the whole API, so the React app handles errors the same way everywhere:

    {"error": {"type": "not_found", "message": "Human-readable text.", "details": ...}}

Unexpected server errors are logged in full but the client only sees a
generic message — no stack traces, file paths or database details.
"""
import logging

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def error_response(http_status, error_type, message, details=None, **extra):
    body = {"type": error_type, "message": message}
    if details is not None:
        body["details"] = details
    body.update(extra)
    return Response({"error": body}, status=http_status)


def api_exception_handler(exc, context):
    if isinstance(exc, Http404):
        # Django's 404 has no error code and its text names the database model.
        exc = NotFound("Not found.")
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled error in %s", context.get("view").__class__.__name__)
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "server_error",
            "Something went wrong on the server. Please try again.",
        )
    if isinstance(exc, ValidationError):
        response.data = {"error": {
            "type": "validation_error", "message": "Some of the submitted values are invalid.",
            "details": response.data,
        }}
    else:
        detail = response.data.get("detail", "") if isinstance(response.data, dict) else response.data
        response.data = {"error": {"type": getattr(exc, "default_code", "error"), "message": str(detail)}}
    return response
