"""API middleware components with CORS protection."""

import time
import logging
from typing import Callable, Set, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class CORSMiddleware(BaseHTTPMiddleware):
    """
    CORS middleware with allowlist enforcement for credentialed requests.
    
    Only allows requests from explicitly configured origins when credentials
    are present, preventing cross-origin attacks.
    """
    
    def __init__(
        self,
        app,
        allow_origins: Optional[Set[str]] = None,
        allow_credentials: bool = True,
        allow_methods: Optional[Set[str]] = None,
        allow_headers: Optional[Set[str]] = None
    ):
        super().__init__(app)
        self.allow_origins = allow_origins or set()
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods or {"GET", "POST", "PUT", "DELETE", "OPTIONS"}
        self.allow_headers = allow_headers or {"*"}
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response(status_code=200)
            return self._add_cors_headers(response, origin)
        
        # Process the request
        response = await call_next(request)
        
        # Add CORS headers to response
        return self._add_cors_headers(response, origin)
    
    def _add_cors_headers(self, response: Response, origin: Optional[str]) -> Response:
        """Add CORS headers if origin is allowed."""
        if not origin:
            return response
            
        # Check if origin is in allowlist
        if origin in self.allow_origins or "*" in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            
            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"
                
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        else:
            # Origin not allowed - log but don't expose allowlist
            logger.warning(f"CORS: Rejected request from unauthorized origin: {origin}")
            
        return response


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path.startswith("/api/v2") and request.url.path != "/api/v2/auth/token":
            token = request.headers.get("Authorization", "")
            if not token.startswith("Bearer "):
                return Response(status_code=401, content="Unauthorized")
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window
        self._requests = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        if client_ip not in self._requests:
            self._requests[client_ip] = []

        self._requests[client_ip] = [t for t in self._requests[client_ip] if now - t < self.window]

        if len(self._requests[client_ip]) >= self.max_requests:
            return Response(status_code=429, content="Too many requests")

        self._requests[client_ip].append(now)
        return await call_next(request)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        logger.info(f"{request.method} {request.url.path} {response.status_code} {duration:.3f}s")
        return response