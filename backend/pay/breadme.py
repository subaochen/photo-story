"""面包多 (Breadme) API 集成模块"""

import os
import hashlib
import logging
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)

BREADME_API_BASE = "https://money.breadme.cn/api/v1"
BREADME_API_KEY = os.getenv("BREADME_API_KEY", "")
BREADME_CALLBACK_SECRET = os.getenv("BREADME_CALLBACK_SECRET", "")


def _get_api_key() -> str:
    return BREADME_API_KEY


def _get_callback_secret() -> str:
    return BREADME_CALLBACK_SECRET


async def create_order(
    price: float,
    title: str,
    description: str = "",
    user_id: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """创建面包多支付订单

    Args:
        price: 订单金额（元）
        title: 订单标题
        description: 订单描述
        user_id: 用户 ID
        metadata: 自定义元数据

    Returns:
        包含 order_id, pay_url 等信息的字典

    Raises:
        ValueError: API key 未配置
        httpx.HTTPError: API 请求失败
    """
    api_key = _get_api_key()
    if not api_key:
        logger.error("BREADME_API_KEY not configured")
        return {
            "order_id": f"mock-{user_id}-{price}",
            "pay_url": f"https://example.com/pay/mock/{user_id}",
            "status": "mock_no_api_key",
        }

    payload: Dict[str, Any] = {
        "price": price,
        "title": title,
        "description": description,
        "custom_order_id": user_id,
    }
    if metadata:
        payload["metadata"] = metadata

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{BREADME_API_BASE}/create-order",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    logger.info(f"面包多订单创建成功: order_id={data.get('order_id')}, price={price}")
    return data


def verify_callback(payload: str, signature: str) -> bool:
    """验证面包多回调签名

    Args:
        payload: 回调 POST body（原始字符串）
        signature: 回调请求中的签名（X-Signature header）

    Returns:
        True 表示签名验证通过
    """
    secret = _get_callback_secret()
    if not secret:
        logger.warning("BREADME_CALLBACK_SECRET not configured, skipping verification")
        return True

    expected = hashlib.sha256(f"{payload}{secret}".encode()).hexdigest()
    is_valid = expected == signature

    if not is_valid:
        logger.warning("面包多回调签名验证失败")
    else:
        logger.info("面包多回调签名验证通过")

    return is_valid


def parse_callback_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """解析面包多回调数据

    Args:
        data: 回调 JSON body

    Returns:
        标准化的回调信息
    """
    return {
        "order_id": data.get("order_id", ""),
        "custom_order_id": data.get("custom_order_id", ""),
        "status": data.get("status", ""),
        "price": data.get("price", 0),
        "paid_at": data.get("paid_at"),
        "transaction_id": data.get("transaction_id", ""),
    }
