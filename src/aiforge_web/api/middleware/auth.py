from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from typing import Optional

security = HTTPBearer(auto_error=False)


async def verify_api_key(token: Optional[str] = Depends(security)):
    """API 密钥验证（可选）"""
    # 如果没有提供 token，允许访问（公开 API）
    if not token:
        return None

    # 这里可以实现具体的 API 密钥验证逻辑
    # 例如：检查数据库、验证 JWT 等

    # 示例验证逻辑
    valid_keys = ["your-api-key-here"]  # 实际应用中从配置或数据库获取

    if token.credentials not in valid_keys:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token.credentials
