"""CreateX AI – Authentication & Identity Verification Module

Provides authentication dependencies and tenant authorization guards.
Strict Security Rules:
1. Rejects invalid or expired Bearer tokens with HTTP 401.
2. NEVER silently downgrades invalid tokens to guest mode.
3. Only requests with NO Authorization header may use the guest flow.
4. Validates project ownership and guest session boundaries.
"""
import re
import logging
from dataclasses import dataclass
from typing import Optional
from fastapi import Header, HTTPException, Query, status

logger = logging.getLogger(__name__)

SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{3,128}$")


@dataclass
class AuthIdentity:
    user_id: Optional[str] = None
    email: Optional[str] = None
    is_authenticated: bool = False


def validate_session_id(session_id: Optional[str]) -> str:
    """Validate guest session ID format to prevent injection or enumeration."""
    HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
    if not session_id or not isinstance(session_id, str):
        raise HTTPException(
            status_code=HTTP_422,
            detail="A valid session_id is required for unauthenticated guest requests.",
        )
    clean_id = session_id.strip()
    if not SESSION_ID_PATTERN.match(clean_id):
        raise HTTPException(
            status_code=HTTP_422,
            detail="Invalid session_id format. Must be 3-128 alphanumeric characters, hyphens, or underscores.",
        )
    return clean_id


async def get_current_identity(authorization: Optional[str] = Header(None)) -> AuthIdentity:
    """
    Authenticate incoming request.

    - If Authorization header is provided:
        * Must start with 'Bearer '.
        * Must validate successfully against Supabase Auth / JWT.
        * If invalid or expired, RAISES HTTP 401 IMMEDIATELY.
        * NEVER silently falls back to guest mode.
    - If Authorization header is omitted:
        * Returns unauthenticated guest identity (is_authenticated=False).
    """
    if authorization is None or authorization.strip() == "":
        return AuthIdentity(user_id=None, email=None, is_authenticated=False)

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    # 1. Test hook: Explicitly permitted ONLY in non-production environments when allow_test_tokens is True.
    # In production, or when allow_test_tokens is False, it FAILS CLOSED with HTTP 401 Unauthorized immediately.
    from app.core.config import settings

    if token.startswith("mock_valid_user_"):
        if not settings.is_production and settings.allow_test_tokens:
            user_id = token.replace("mock_valid_user_", "").strip()
            return AuthIdentity(user_id=user_id, email=f"{user_id}@example.com", is_authenticated=True)
        else:
            logger.warning("Mock token rejected: forbidden in production or allow_test_tokens is disabled.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token is invalid or expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 2. Live Supabase Auth verification
    from app.services.supabase_service import is_supabase_configured, get_supabase

    if is_supabase_configured():
        try:
            supabase = get_supabase()
            user_response = supabase.auth.get_user(token)
            if user_response and getattr(user_response, "user", None):
                u = user_response.user
                return AuthIdentity(
                    user_id=str(u.id),
                    email=getattr(u, "email", None),
                    is_authenticated=True,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired authentication credentials.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Supabase token verification error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token is invalid or expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 3. Local JWT Secret verification (if configured in settings)
    from app.core.config import settings
    jwt_secret = getattr(settings, "supabase_jwt_secret", "")
    if jwt_secret:
        try:
            import jwt
            payload = jwt.decode(token, jwt_secret, algorithms=["HS256"], audience="authenticated")
            sub = payload.get("sub")
            if not sub:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing subject (sub) claim.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return AuthIdentity(user_id=str(sub), email=payload.get("email"), is_authenticated=True)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # If Supabase is unconfigured and token is not recognized -> 401
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_project_ownership(
    project: dict,
    identity: AuthIdentity,
    session_id: Optional[str] = None,
) -> None:
    """
    Enforce strict tenant and guest session boundaries.
    Raises HTTP 404 (preventing resource enumeration) if unauthorized.
    """
    project_owner_id = project.get("user_id")
    project_session_id = project.get("session_id")

    # Case 1: Project is owned by a registered user
    if project_owner_id is not None:
        if not identity.is_authenticated or identity.user_id != str(project_owner_id):
            logger.warning(
                "Access denied to project %s: expected user %s, got user %s (is_auth=%s)",
                project.get("id"),
                project_owner_id,
                identity.user_id,
                identity.is_authenticated,
            )
            # Use 404 to avoid leaking project existence to attackers
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        return

    # Case 2: Project is a guest session project (user_id is None)
    clean_session = (session_id or "").strip()
    if not clean_session or clean_session != project_session_id:
        logger.warning(
            "Access denied to guest project %s: session mismatch (expected %s, got %s)",
            project.get("id"),
            project_session_id,
            clean_session,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
