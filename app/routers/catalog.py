from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from .. import database
from ..schemas import ProductOut, ProductPage


router = APIRouter(prefix="/api/products", tags=["Catalog"])


@router.get("", response_model=ProductPage, summary="List and search products")
async def products(
    search: str | None = Query(default=None, max_length=80),
    category: str | None = Query(default=None, max_length=40),
    sort: str = Query(default="name", pattern=r"^(name|price_asc|price_desc|rating|newest)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
) -> ProductPage:
    result = database.list_products(search, category, sort, page, page_size)
    return ProductPage(**result)


@router.get("/{product_id}", response_model=ProductOut, summary="Read one product")
async def product_detail(product_id: int) -> ProductOut:
    product = database.get_product(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} was not found",
        )
    return ProductOut(**product)

