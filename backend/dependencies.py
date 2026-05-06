import os
from fastapi import Header, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address

ADMIN_KEY = os.getenv("ADMIN_API_KEY", "")

limiter = Limiter(key_func=get_remote_address)


async def require_admin_key(x_api_key: str = Header(default="")):
    if not ADMIN_KEY:
        return  # local dev — no key configured, all requests allowed
    if x_api_key != ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header",
        )
