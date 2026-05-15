import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Header, Form
from pydantic import BaseModel, Field

from .breadme import create_order, verify_callback, parse_callback_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pay", tags=["pay"])


class CreateOrderRequest(BaseModel):
    price: float = Field(..., gt=0, le=10000, description="订单金额（元）")
    title: str = Field(..., min_length=1, max_length=100, description="订单标题")
    description: str = Field("", max_length=500, description="订单描述")


class CallbackResult(BaseModel):
    order_id: str
    user_id: str
    status: str
    price: float


@router.post("/create-order")
async def post_create_order(request: CreateOrderRequest):
    if not request.title:
        raise HTTPException(status_code=400, detail="订单标题不能为空")

    try:
        result = await create_order(
            price=request.price,
            title=request.title,
            description=request.description,
        )
    except Exception as e:
        logger.error(f"创建支付订单失败: {e}")
        raise HTTPException(status_code=502, detail=f"支付服务不可用: {str(e)}")

    return {
        "order_id": result.get("order_id"),
        "pay_url": result.get("pay_url"),
        "status": result.get("status", "created"),
    }


@router.post("/callback")
async def post_callback(request: Request, x_signature: Optional[str] = Header(None, alias="X-Signature")):
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")

    if x_signature and not verify_callback(body_str, x_signature):
        raise HTTPException(status_code=401, detail="签名验证失败")

    try:
        data = json.loads(body_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON 格式")

    parsed = parse_callback_data(data)

    if parsed["status"] == "paid":
        logger.info(f"支付成功: order_id={parsed['order_id']}, user={parsed['custom_order_id']}")
        # TODO: update user is_paid status, increment usage_limit, etc.
        return {"result": "success", "order_id": parsed["order_id"]}

    logger.info(f"支付回调: order_id={parsed['order_id']}, status={parsed['status']}")
    return {"result": "received", "order_id": parsed["order_id"]}
