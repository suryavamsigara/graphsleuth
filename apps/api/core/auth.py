import os
import jwt
from dataclasses import dataclass
from fastapi import Header, HTTPException

# Supabase issues HS256 JWTs signed with the project's JWT secret.
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")


@dataclass
class AuthedUser:
    id: str
    email: str | None = None


def _decode(token: str) -> AuthedUser:
    if not SUPABASE_JWT_SECRET:
        raise RuntimeError("SUPABASE_JWT_SECRET is not set")
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing subject claim")

    return AuthedUser(id=sub, email=payload.get("email"))


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


async def get_current_user(authorization: str | None = Header(default=None)) -> AuthedUser:
    token = _extract_bearer(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return _decode(token)


async def get_current_user_optional(authorization: str | None = Header(default=None)) -> AuthedUser | None:
    token = _extract_bearer(authorization)
    if not token:
        return None
    try:
        return _decode(token)
    except HTTPException:
        return None
