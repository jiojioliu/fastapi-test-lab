from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from .. import database
from ..dependencies import CurrentUser, require_admin, require_order_user
from ..schemas import OrderCreate, OrderOut, OrderPage, OrderStatusUpdate


router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.get("", response_model=OrderPage, summary="List the current user's orders")
async def list_orders(
    order_status: str | None = Query(
        default=None,
        alias="status",
        pattern=r"^(pending|confirmed|shipped|completed|cancelled)$",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    user: CurrentUser = Depends(require_order_user),
) -> OrderPage:
    result = database.list_orders(
        user.id, user.is_admin, order_status, page, page_size
    )
    return OrderPage(**result)


@router.post(
    "",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an order",
)
async def create_order(
    payload: OrderCreate,
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", max_length=128
    ),
    user: CurrentUser = Depends(require_order_user),
) -> OrderOut:
    try:
        order, created = database.create_order(
            user.id,
            [item.model_dump() for item in payload.items],
            payload.note,
            idempotency_key,
            payload.payment_method,
        )
    except database.OrderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    if not created:
        # Replayed requests still carry the original entity in the body. The
        # status is kept at 201 for easy JMeter/Postman assertions.
        order["_idempotent_replay"] = True
    return OrderOut(**order)


@router.get("/{order_id}", response_model=OrderOut, summary="Read an order")
async def order_detail(
    order_id: str,
    user: CurrentUser = Depends(require_order_user),
) -> OrderOut:
    order = database.get_order(order_id, user.id, user.is_admin)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} was not found",
        )
    return OrderOut(**order)


@router.patch(
    "/{order_id}/status",
    response_model=OrderOut,
    summary="Change order status (admin only)",
)
async def update_status(
    order_id: str,
    payload: OrderStatusUpdate,
    _: CurrentUser = Depends(require_admin),
) -> OrderOut:
    order = database.update_order_status(order_id, payload.status)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} was not found",
        )
    return OrderOut(**order)

