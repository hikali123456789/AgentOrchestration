"""Tests for CORS middleware."""

import pytest
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient

from src.api.middleware import CORSMiddleware, AuthMiddleware


class TestCORSMiddleware:
    """Tests for CORS allowlist enforcement."""

    def test_allowed_origin(self):
        async def app(request):
            return Response("OK")
        
        middleware = CORSMiddleware(app, allow_origins={"https://example.com"})
        
        class MockRequest:
            method = "GET"
            headers = {"origin": "https://example.com"}
        
        # Origin in allowlist gets CORS headers
        response = middleware._add_cors_headers(Response("OK"), "https://example.com")
        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "https://example.com"

    def test_disallowed_origin(self):
        middleware = CORSMiddleware(lambda r: Response("OK"), allow_origins={"https://example.com"})
        
        # Origin not in allowlist - no CORS headers
        response = middleware._add_cors_headers(Response("OK"), "https://evil.com")
        assert "Access-Control-Allow-Origin" not in response.headers

    def test_preflight_request(self):
        from starlette.applications import Starlette
        
        app = Starlette()
        app.add_middleware(CORSMiddleware, allow_origins={"https://example.com"})
        
        client = TestClient(app)
        response = client.options("/", headers={"origin": "https://example.com"})
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers

    def test_credentials_header(self):
        middleware = CORSMiddleware(
            lambda r: Response("OK"),
            allow_origins={"https://example.com"},
            allow_credentials=True
        )
        response = middleware._add_cors_headers(Response("OK"), "https://example.com")
        assert response.headers.get("Access-Control-Allow-Credentials") == "true"

    def test_no_origin_header(self):
        middleware = CORSMiddleware(lambda r: Response("OK"), allow_origins={"https://example.com"})
        response = middleware._add_cors_headers(Response("OK"), None)
        assert "Access-Control-Allow-Origin" not in response.headers


class TestCORSWithAuth:
    """Tests for CORS + Auth middleware interaction."""

    def test_cors_before_auth(self):
        """CORS headers should be added even for 401 responses."""
        from starlette.applications import Starlette
        
        app = Starlette()
        app.add_middleware(CORSMiddleware, allow_origins={"https://example.com"})
        app.add_middleware(AuthMiddleware)
        
        client = TestClient(app)
        response = client.get(
            "/api/v2/test",
            headers={"origin": "https://example.com"}
        )
        # Should get 401 but still have CORS headers
        assert "Access-Control-Allow-Origin" in response.headers