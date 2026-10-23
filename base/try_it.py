"""Run this file to see what your code does:   python try_it.py
It builds a few products in memory (nothing is saved anywhere) and tries your two tasks. Do not change this file."""
import asyncio
from decimal import Decimal

try:
    from app.db.models import Category, Product
    from app.fakes import FakeCategoryRepository, FakeProductRepository
    from app.schemas.product import ProductCreate, ProductQuery
    from app.services import product_mapper
    from app.services.product_service import ProductService
except Exception as exc:  # a mistake in one of the files would stop the import
    raise SystemExit(f"a file has a problem -> {type(exc).__name__}: {exc}")


def make_product(id, title, stock, category=None):
    return Product(id=id, title=title, price=Decimal("5.00"), stock=stock, category=category)


def show(label, make_text):
    """Print the label and the text. If the code under test breaks, print a short message instead of a long error."""
    try:
        text = make_text()
    except Exception as exc:
        text = f"something is wrong -> {type(exc).__name__}: {exc}"
    print(f"  {label:<30}: {text}")


def titles(products):
    return ", ".join(p.title for p in products) if products else "(nothing)"


beauty = make_product(1, "Lip Gloss", 3, Category(name="beauty"))
mug = make_product(2, "Mug", 40)

print("Task 1: to_dict")
show("title and price", lambda: "{} {}".format(*[product_mapper.to_dict(beauty)[k] for k in ("title", "price")]))
show("category name", lambda: product_mapper.to_dict(beauty)["category"])
show("no category", lambda: product_mapper.to_dict(mug)["category"])
for stock in (9, 10, 11):
    show(f"low_stock for {stock}", lambda stock=stock: product_mapper.to_dict(make_product(3, "X", stock))["low_stock"])

print("Task 2: FakeProductRepository")
fake = FakeProductRepository([mug, beauty])
show("get_by_id(1)", lambda: asyncio.run(fake.get_by_id(1)).title)
show("get_by_id(99)", lambda: asyncio.run(fake.get_by_id(99)))
show("search", lambda: titles(asyncio.run(fake.search(ProductQuery()))))
show("add: the next id", lambda: asyncio.run(fake.add(make_product(None, "Lamp", 5))).id)
show("add: first on an empty shelf", lambda: asyncio.run(FakeProductRepository().add(make_product(None, "Lamp", 5))).id)
service = ProductService(FakeProductRepository([beauty, mug]), FakeCategoryRepository())
show("the service, get", lambda: "{title} low_stock={low_stock}".format(**asyncio.run(service.get_by_id(1))))
show("the service, list", lambda: ", ".join(p["title"] for p in asyncio.run(service.list_products(ProductQuery()))))
show("the service, create", lambda: "id {id}, category {category}".format(**asyncio.run(service.create(ProductCreate(title="Toy Robot", price=Decimal("7.50"), stock=40, category="toys")))))
