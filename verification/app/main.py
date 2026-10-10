"""Intentionally vulnerable BOLA application (OWASP API1:2023 benchmark).

Vulnerability summary:
The endpoint /api/documents/<doc_id> verifies authentication (X-User-Id)
but fails to verify that the requesting user owns or has access to the requested document.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Tuple
from urllib.parse import parse_qs

from .database import DocumentDatabase

db = DocumentDatabase()


def get_current_user(environ: Dict[str, Any]) -> str | None:
    """Extract authenticated user identity from request headers."""
    # WSGI converts HTTP header X-User-Id to HTTP_X_USER_ID
    return environ.get("HTTP_X_USER_ID")


def application(environ: Dict[str, Any], start_response: Callable) -> List[bytes]:
    """WSGI entrypoint for the BOLA benchmark service."""
    path = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "GET")

    def json_response(status_code: int, payload: Dict[str, Any]) -> List[bytes]:
        status_text = {
            200: "200 OK",
            400: "400 Bad Request",
            401: "401 Unauthorized",
            403: "403 Forbidden",
            404: "404 Not Found",
            500: "500 Internal Server Error",
        }.get(status_code, f"{status_code} Unknown")
        response_body = json.dumps(payload).encode("utf-8")
        headers = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body))),
        ]
        start_response(status_text, headers)
        return [response_body]

    # Health check
    if path == "/health" and method == "GET":
        return json_response(200, {"status": "ok", "app": "sentinel-bola-target"})

    # Authentication gate
    current_user = get_current_user(environ)
    if not current_user:
        return json_response(401, {"error": "Authentication required: missing X-User-Id header"})

    # Validate user format
    if not re.match(r"^[a-zA-Z0-9_\-]+$", current_user):
        return json_response(400, {"error": "Invalid characters in X-User-Id header"})

    # GET /api/documents - list user's documents
    if path == "/api/documents" and method == "GET":
        docs = [d for d in db.list_all() if d.get("owner_id") == current_user]
        return json_response(200, {"documents": docs, "user": current_user})

    # GET /api/documents/<doc_id>
    doc_match = re.match(r"^/api/documents/([a-zA-Z0-9_\-]+)$", path)
    if doc_match and method == "GET":
        doc_id = doc_match.group(1)
        doc = db.get_by_id(doc_id)
        if doc is None:
            return json_response(404, {"error": f"Document '{doc_id}' not found"})

        # VULNERABLE IMPLEMENTATION (BOLA / IDOR):
        # The code fails to check: if doc.get("owner_id") != current_user: return 403 Forbidden
        return json_response(200, doc)

    return json_response(404, {"error": f"Route not found: {method} {path}"})


if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    port = 8000
    print(f"Starting SENTINEL-X BOLA target application on port {port}...")
    server = make_server("0.0.0.0", port, application)
    server.serve_forever()
