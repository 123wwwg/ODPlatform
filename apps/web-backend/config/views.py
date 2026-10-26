from __future__ import annotations

from django.conf import settings
from django.http import FileResponse, HttpRequest


def frontend_index(request: HttpRequest) -> FileResponse:
    response = FileResponse(
        (settings.BASE_DIR / "frontend" / "index.html").open("rb"),
        content_type="text/html; charset=utf-8",
    )
    response["Cache-Control"] = "no-cache"
    return response
