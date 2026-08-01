import os
import jwt
from dotenv import load_dotenv
from dataclasses import dataclass
from fastapi import Header, HTTPException

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
JWKS_URL = f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

jwk_client = jwt.PyJWKClient(
    JWKS_URL,
    headers={
        "apikey": SUPABASE_ANON_KEY or "",
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}" if SUPABASE_ANON_KEY else ""
    }
)

@dataclass
class AuthedUser:
    id: str
    email: str | None = None


def _decode(token: str) -> AuthedUser:
    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
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
