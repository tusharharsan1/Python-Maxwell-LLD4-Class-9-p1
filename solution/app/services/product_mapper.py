"""Turns a Product into the dictionary that the client receives.

This is the finished file. The function is PURE: it uses only the product it receives, so a test can call it in one line.
"""
from app.db.models import Product

LOW_STOCK_LIMIT = 10


def to_dict(product: Product) -> dict:
    return {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "price": product.price,
        "stock": product.stock,
        "image_url": product.image_url,
        # Only the NAME of the category. A product with no category has product.category equal to None,
        # and None has no .name, so choose first.
        "category": product.category.name if product.category else None,
        # 10 left is also low, so it is "less than or equal". The limit comes from the constant, not from a bare 10.
        "low_stock": product.stock <= LOW_STOCK_LIMIT,
    }
