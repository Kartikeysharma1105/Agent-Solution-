"""WSGI TestClient for deterministic in-process testing of the target app."""

from __future__ import annotations

import io
import json
import os
from typing import Any, Dict, Optional, Tuple


class TestResponse:
    """Encapsulates status code, headers, and json data."""

    def __init__(self, status_code: int, headers: Dict[str, str], body: bytes) -> None:
        self.status_code = status_code
        self.headers = headers
        self.body = body

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")

    def json(self) -> Any:
        return json.loads(self.text)


class AppClient:
    """Client for testing target WSGI application."""

    def __init__(self) -> None:
        # Dynamically import the target application
        from verification.app.main import application, db
        self.application = application
        self.db = db

    def get(self, path: str, headers: Optional[Dict[str, str]] = None) -> TestResponse:
        hdrs = headers or {}
        environ: Dict[str, Any] = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": path,
            "QUERY_STRING": "",
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "8000",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": io.BytesIO(b""),
            "wsgi.errors": io.StringIO(),
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
        }

        for k, v in hdrs.items():
            key = "HTTP_" + k.upper().replace("-", "_")
            environ[key] = v

        captured_status: list[str] = []
        captured_headers: list[tuple[str, str]] = []

        def start_response(status: str, response_headers: list[tuple[str, str]], exc_info=None):
            captured_status.append(status)
            captured_headers.extend(response_headers)

        body_chunks = self.application(environ, start_response)
        body = b"".join(body_chunks)
        status_code = int(captured_status[0].split()[0]) if captured_status else 500
        headers_dict = dict(captured_headers)

        return TestResponse(status_code, headers_dict, body)
