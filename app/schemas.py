from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, examples=["admin"])
    password: str = Field(min_length=6, max_length=128, examples=["admin123"])


class RegisterRequest(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=32,
        pattern=r"^[A-Za-z0-9_.-]+$",
        examples=["api_student"],
    )
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=48)


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    category: str
    price: float
    stock: int
    rating: float
    description: str
    accent: str
    created_at: str


class ProductPage(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int
    pages: int
    categories: list[str]


class OrderItemInput(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=20)


class OrderCreate(BaseModel):
    items: list[OrderItemInput] = Field(min_length=1, max_length=20)
    note: str | None = Field(default=None, max_length=200)
    payment_method: Literal["alipay", "wechat", "bank_card"] = "alipay"

    @field_validator("items")
    @classmethod
    def unique_products(cls, items: list[OrderItemInput]) -> list[OrderItemInput]:
        ids = [item.product_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Each product can appear only once")
        return items


class OrderItemOut(BaseModel):
    product_id: int
    product_name: str
    unit_price: float
    quantity: int
    line_total: float


class OrderOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    user_id: int
    username: str
    status: str
    items: list[OrderItemOut]
    subtotal: float
    tax: float
    total: float
    payment_method: str
    payment_status: str
    note: str | None
    idempotency_key: str | None
    created_at: str
    updated_at: str


class OrderPage(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    page_size: int
    pages: int


class OrderStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(pending|confirmed|shipped|completed|cancelled)$")


class ContactForm(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=120)
    subject: str = Field(min_length=2, max_length=80)
    message: str = Field(min_length=5, max_length=1000)


class EchoResponse(BaseModel):
    request_id: str
    method: str
    path: str
    query: dict[str, Any]
    headers: dict[str, str]
    body: Any = None
    client: str
    received_at: str

