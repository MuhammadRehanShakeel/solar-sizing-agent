"""
auth.py - "Who is calling, and are they allowed?"  (staff pages only)

Customers chat WITHOUT an account. Staff (admin / sales) log in to see leads and change prices.
    current_user = Depends(STAFF)    admin or sales
    current_user = Depends(ADMIN)    admin only (prices, users)

The user is re-read from the database on every request, so a disabled account or a changed
role takes effect immediately.
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token
from app.database import execute_query

bearer = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if credentials is None or not credentials.credentials:
        raise HTTPException(401, "Please log in.")
    payload = decode_token(credentials.credentials)
    if payload.get("scope"):                      # quote links etc. are not login tokens
        raise HTTPException(401, "Please log in.")
    user = execute_query("SELECT user_id, full_name, email, role, is_active, token_version FROM Users "
                         "WHERE user_id = ?", (payload.get("user_id"),), fetch_one=True)
    if not user or not user["is_active"]:
        raise HTTPException(401, "This account is disabled. Contact an admin.")
    if (user.get("token_version") or 0) != payload.get("tv", 0):
        raise HTTPException(401, "Your session has ended. Please log in again.")
    return user


def require_roles(*roles):
    def checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in roles:
            raise HTTPException(403, "You do not have permission for this action.")
        return current_user
    return checker


ADMIN = require_roles("admin")
STAFF = require_roles("admin", "sales")
