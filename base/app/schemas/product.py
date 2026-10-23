from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    title: str = Field(min_length=3)
    price: Decimal = Field(gt=0)
    stock: int = Field(ge=0)
    category: Optional[str] = None


class ProductQuery(BaseModel):
    page: int = Field(default=0, ge=0)
    size: int = Field(default=10, ge=1, le=100)
    sort_by: Literal["id", "title", "price", "stock"] = "id"
    order: Literal["asc", "desc"] = "asc"
    keyword: Optional[str] = None
    min_price: Optional[Decimal] = Field(default=None, ge=0)
    max_price: Optional[Decimal] = Field(default=None, ge=0)
