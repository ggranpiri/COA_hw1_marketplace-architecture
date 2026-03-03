from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Callable

from fastapi import FastAPI, Request, Response

from app.security import decode_token


def _mask_sensitive(body: str) -> str:
    # простая маска для пароля в JSON
    try:
        data = json.loads(body)
        if isinstance(data, dict) and "password" in data:
            data["password"] = "***"
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return body


def install_access_log(app: FastAPI) -> None:
    @app.middleware("http")
    async def access_log_middleware(request: Request, call_next: Callable):
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        body_text = ""
        if request.method in ("POST", "PUT", "DELETE"):
            raw = await request.body()
            body_text = _mask_sensitive(raw.decode("utf-8", errors="ignore"))

            async def receive():
                return {"type": "http.request", "body": raw}

            request._receive = receive  # noqa: SLF001

        response: Response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        user_id = None
        auth = request.headers.get("authorization")
        if auth and auth.startswith("Bearer "):
            token = auth[7:].strip()
            try:
                payload = decode_token(token)
                if payload.get("type") == "access":
                    user_id = int(payload["sub"])
            except Exception:
                user_id = None

        log_record = {
            "request_id": request_id,
            "method": request.method,
            "endpoint": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if body_text:
            log_record["body"] = body_text

        print(json.dumps(log_record, ensure_ascii=False))
        response.headers["X-Request-Id"] = request_id
        return response