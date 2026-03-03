from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, error_code: str, status_code: int, message: str, details: dict | None = None):
        self.error_code = error_code
        self.status_code = status_code
        self.message = message
        self.details = details or {}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": exc.error_code, "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError):
        fields = []
        for e in exc.errors():
            loc = ".".join(str(x) for x in e.get("loc", []) if x != "body")
            fields.append({"field": loc or "body", "message": e.get("msg", "invalid")})
        return JSONResponse(
            status_code=400,
            content={"error_code": "VALIDATION_ERROR", "message": "Validation failed", "details": {"fields": fields}},
        )