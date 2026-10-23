import enum
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class State(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)
    state: Mapped[State] = mapped_column(default=State.ACTIVE)


class Category(Base):
    __tablename__ = "category"

    name: Mapped[str] = mapped_column(String(100))
    products: Mapped[List["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "product"

    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    stock: Mapped[int]
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("category.id"))
    category: Mapped[Optional[Category]] = relationship(back_populates="products")
