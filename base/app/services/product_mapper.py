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
        # TODO 1: "category": the NAME of the product's category, or None when the product has no category.
        # TODO 2: "low_stock": True when the stock is LOW_STOCK_LIMIT (10) or fewer, otherwise False.
    }
