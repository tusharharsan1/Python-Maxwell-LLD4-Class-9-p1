"""Stand-ins for the real repositories, to use in tests. This is the finished file."""
from app.db.models import Category


class FakeCategoryRepository:
    """Already finished. It is the example for the fake product repository below."""

    async def get_or_create(self, name):
        return Category(name=name)


class FakeProductRepository:
    """A stand-in for the real repository: the same methods, but the products live in a dictionary in memory."""

    def __init__(self, products=None):
        self.products = {}
        for product in products or []:
            self.products[product.id] = product

    async def get_by_id(self, product_id):
        # dict.get gives None when the key is missing (a plain self.products[product_id] would raise KeyError).
        return self.products.get(product_id)

    async def search(self, query):
        # The query is ignored. sorted() builds a NEW list, so the caller cannot change the fake by changing the list.
        return sorted(self.products.values(), key=lambda p: p.id)

    async def add(self, product):
        # The biggest id plus 1. default=0 makes an empty fake give the id 1.
        product.id = max(self.products, default=0) + 1
        self.products[product.id] = product
        return product
