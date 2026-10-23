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
        # TODO 3: return the product that has this id, or None when there is no such product.
        ...

    async def search(self, query):
        # TODO 4: return all the products in a list, sorted by their ids. (The query is ignored.)
        ...

    async def add(self, product):
        # TODO 5: give the product the next id: the biggest id in self.products plus 1 (the first product gets 1).
        #         Keep the product in self.products, and return it.
        ...
