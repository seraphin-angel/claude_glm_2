from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt

from app.config.settings import get_settings

security = HTTPBearer()


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """JWT アクセストークンを生成する。"""
    settings = get_settings()
    to_encode = {**data}
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.jwt_secret_key.get_secret_value(), algorithm=settings.jwt_algorithm)


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """JWT トークンを検証し、ペイロードを返す。"""
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンの有効期限が切れています",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンが無効です",
        )


def get_user_id_from_payload(payload: dict) -> str | None:
    """ペイロードからユーザーIDを取得する。

    JWT標準の `sub` クレームのみを参照する。
    他のフィールド（user_id, userId, id など）は無視する。

    Args:
        payload: JWT ペイロード

    Returns:
        ユーザーID（`sub` クレームが存在しない場合はNone）
    """
    sub = payload.get("sub")
    if sub is not None:
        return str(sub)
    return None


async def verify_token_and_get_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """JWT トークンを検証し、ユーザーIDを返す。

    Returns:
        ユーザーID

    Raises:
        HTTPException: トークンが無効、またはユーザーIDが含まれていない場合
    """
    payload = await verify_token(credentials)
    user_id = get_user_id_from_payload(payload)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンにユーザーIDが含まれていません",
        )
    return user_id
