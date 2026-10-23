import asyncio
import inspect
import os
import random
import sys
import unittest
from decimal import Decimal
from unittest import mock

# Lets this file run directly (python tests/test_fake_repository.py) from any folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.errors import ProductNotFoundError
from app.db.models import Category, Product
from app.fakes import FakeCategoryRepository, FakeProductRepository
from app.schemas.product import ProductCreate, ProductQuery
from app.services import product_mapper
from app.services.product_mapper import LOW_STOCK_LIMIT, to_dict
from app.services.product_service import ProductService

# ---------------------------------------------------------------------------
# Test data: what the README says
# ---------------------------------------------------------------------------

# The eight keys of the dictionary, as the README table lists them.
ALL_KEYS = {"id", "title", "description", "price", "stock", "image_url", "category", "low_stock"}

# The README table for low_stock: (the stock, low_stock). 10 is the edge.
README_STOCK_ROWS = [(0, True), (9, True), (10, True), (11, False)]


# ---------------------------------------------------------------------------
# Helpers: keep the tests short and readable
# ---------------------------------------------------------------------------

def run(coroutine):
    """Run one `async def` call to the end and give back its answer (the fake needs no database and no server)."""
    return asyncio.run(coroutine)


def make_product(id=None, title="Mug", stock=40, category=None, price="5.00", description=None, image_url=None):
    """A new Product object in memory. Nothing is saved anywhere."""
    return Product(
        id=id, title=title, description=description, price=Decimal(price),
        stock=stock, image_url=image_url, category=category,
    )


def make_fake(*ids):
    """A new FakeProductRepository that already holds one product for each id, given in this order."""
    return FakeProductRepository([make_product(id=i, title=f"Product {i}") for i in ids])


def make_service(*ids):
    """A ProductService that works on a fake repository (with the given ids) and a fake category repository."""
    return ProductService(make_fake(*ids), FakeCategoryRepository())


def snapshot(product):
    """The fields of a product as a plain tuple, to compare 'before' and 'after'."""
    category = product.category
    return (product.id, product.title, product.description, product.price, product.stock, product.image_url,
            category, category.name if category else None)


# ===========================================================================
# TASK 1: the pure function to_dict
# ===========================================================================

class ToDictTests(unittest.TestCase):
    """Task 1: `to_dict` turns a Product into a dictionary. It needs no database and no server."""

    def test_the_function_keeps_its_name_and_parameter(self):
        """The function is still called `to_dict`, and its only parameter is still called `product`."""
        self.assertEqual(list(inspect.signature(to_dict).parameters), ["product"])

    def test_the_dictionary_has_exactly_the_eight_keys(self):
        """The eight keys of the README table, and no other key.

        Anti-bypass: a missing key (`KeyError` later) or an extra key is seen here.
        """
        self.assertEqual(set(to_dict(make_product(id=1))), ALL_KEYS)

    def test_the_six_copied_keys_are_copied_as_they_are(self):
        """`id`, `title`, `description`, `price`, `stock` and `image_url` hold what the product holds."""
        product = make_product(
            id=7, title="Lip Gloss", description="Shiny", price="12.99", stock=3, image_url="http://img/1.png",
            category=Category(name="beauty"),
        )
        result = to_dict(product)
        self.assertEqual(result["id"], 7)
        self.assertEqual(result["title"], "Lip Gloss")
        self.assertEqual(result["description"], "Shiny")
        self.assertEqual(result["stock"], 3)
        self.assertEqual(result["image_url"], "http://img/1.png")

    def test_missing_description_and_image_stay_none(self):
        """A product without a description or an image gives `None` for both."""
        result = to_dict(make_product(id=1))
        self.assertIsNone(result["description"])
        self.assertIsNone(result["image_url"])

    def test_the_price_stays_a_decimal(self):
        """`price` is the same Decimal as in the product: not a float, not text, nothing rounded."""
        for price in ("5.00", "12.99", "0.10", "19.999", "12345678901234567.89"):
            with self.subTest(price=price):
                result = to_dict(make_product(id=1, price=price))
                self.assertIsInstance(result["price"], Decimal)
                self.assertEqual(result["price"], Decimal(price))
                self.assertEqual(str(result["price"]), str(Decimal(price)))

    # ---- category

    def test_the_category_is_the_name_of_the_category(self):
        """A product with `Category(name="beauty")` gives the text "beauty", not the Category object."""
        for name in ("beauty", "home decor", "Toys & Games"):
            with self.subTest(name=name):
                result = to_dict(make_product(id=1, category=Category(name=name)))
                self.assertEqual(result["category"], name)
                self.assertIs(type(result["category"]), str)

    def test_no_category_gives_none(self):
        """A product with no category gives `None` for `category`, and does not raise an error."""
        result = to_dict(make_product(id=1, category=None))
        self.assertIn("category", result)
        self.assertIsNone(result["category"])

    # ---- low_stock

    def test_the_readme_table_for_low_stock(self):
        """The table of the README: 0, 9 and 10 are low; 11 is not. 10 is the edge, and it is low."""
        for stock, expected in README_STOCK_ROWS:
            with self.subTest(stock=stock):
                self.assertIs(to_dict(make_product(id=1, stock=stock))["low_stock"], expected)

    def test_low_stock_around_the_limit_and_far_from_it(self):
        """One less than the limit, the limit, one more, and some far values."""
        cases = [(1, True), (5, True), (LOW_STOCK_LIMIT - 1, True), (LOW_STOCK_LIMIT, True),
                 (LOW_STOCK_LIMIT + 1, False), (11, False), (12, False), (50, False), (10000, False)]
        for stock, expected in cases:
            with self.subTest(stock=stock):
                self.assertIs(to_dict(make_product(id=1, stock=stock))["low_stock"], expected)

    def test_low_stock_is_a_real_true_or_false(self):
        """`low_stock` is `True` or `False`, never a number such as 1 or 0."""
        for stock in (0, 10, 11):
            with self.subTest(stock=stock):
                self.assertIsInstance(to_dict(make_product(id=1, stock=stock))["low_stock"], bool)

    def test_the_limit_comes_from_the_constant(self):
        """The rule uses `LOW_STOCK_LIMIT`, so the number lives in one place.

        Anti-bypass: the constant is changed to 3 for the length of the test. A function with a bare `10` in it
        still says that 10 is low, and fails here.
        """
        with mock.patch.object(product_mapper, "LOW_STOCK_LIMIT", 3):
            self.assertIs(to_dict(make_product(id=1, stock=3))["low_stock"], True)
            self.assertIs(to_dict(make_product(id=1, stock=4))["low_stock"], False)
            self.assertIs(to_dict(make_product(id=1, stock=10))["low_stock"], False)

    # ---- the function is pure

    def test_the_product_is_not_changed(self):
        """After the call the product has the same values as before (and the same category object)."""
        product = make_product(id=4, title="Lamp", stock=2, price="19.99", category=Category(name="home"))
        before = snapshot(product)
        to_dict(product)
        self.assertEqual(snapshot(product), before)

    def test_every_call_gives_a_new_dictionary(self):
        """Two calls give two equal dictionaries that are not the same object. Changing one does not change the other.

        Anti-bypass: a dictionary built once and reused would be shared by all the callers.
        """
        product = make_product(id=1, title="Mug")
        first, second = to_dict(product), to_dict(product)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        first["title"] = "Changed"
        self.assertEqual(product.title, "Mug")
        self.assertEqual(to_dict(product)["title"], "Mug")

    def test_two_products_give_two_different_dictionaries(self):
        """The answer depends only on the product it is given (nothing is remembered from the call before)."""
        beauty = make_product(id=1, title="Lip Gloss", stock=3, category=Category(name="beauty"))
        plain = make_product(id=2, title="Mug", stock=40)
        first, second, again = to_dict(beauty), to_dict(plain), to_dict(beauty)
        self.assertEqual((second["title"], second["category"], second["low_stock"]), ("Mug", None, False))
        self.assertEqual(first, again)

    def test_many_random_products_match_the_rules(self):
        """300 random products are checked against a dictionary that the test builds by hand.

        Anti-bypass: the products are made by the test, so a function that only knows the README examples fails.
        """
        generator = random.Random(2024)
        wrong = []
        for _ in range(300):
            category = Category(name=generator.choice(["beauty", "toys", "home decor", "food"])) if generator.random() < 0.6 else None
            product = make_product(
                id=generator.randint(1, 500),
                title=generator.choice(["Mug", "Lip Gloss", "Lamp", "Toy Robot", "Kettle"]),
                stock=generator.randint(0, 25),
                price=f"{generator.randint(1, 9999)}.{generator.randint(0, 99):02d}",
                category=category,
                description=generator.choice([None, "A nice thing"]),
                image_url=generator.choice([None, "http://img/x.png"]),
            )
            expected = {
                "id": product.id, "title": product.title, "description": product.description, "price": product.price,
                "stock": product.stock, "image_url": product.image_url,
                "category": category.name if category else None,
                "low_stock": product.stock <= 10,
            }
            if to_dict(product) != expected:
                wrong.append(f"  stock {product.stock}, category {expected['category']!r}\n    expected {expected}\n    got      {to_dict(product)}")
        if wrong:
            self.fail(f"{len(wrong)} of 300 random products were wrong. The first ones:\n" + "\n".join(wrong[:3]))


# ===========================================================================
# TASK 2: the class FakeProductRepository (called directly)
# ===========================================================================

class FakeGetByIdTests(unittest.TestCase):
    """Task 2, `get_by_id`: the product with that id, or `None`."""

    def test_it_finds_a_product_by_its_id(self):
        """The answer is the SAME product object that was put in, for each id."""
        products = [make_product(id=1, title="Lip Gloss"), make_product(id=2, title="Mug"), make_product(id=9, title="Lamp")]
        fake = FakeProductRepository(products)
        for product in products:
            with self.subTest(id=product.id):
                self.assertIs(run(fake.get_by_id(product.id)), product)

    def test_a_missing_id_gives_none_and_no_error(self):
        """An id that is not in the fake gives `None`. (A plain `self.products[id]` raises `KeyError` instead.)"""
        fake = make_fake(1, 2, 5)
        for missing in (99, 0, 3, 4, -1):
            with self.subTest(id=missing):
                self.assertIsNone(run(fake.get_by_id(missing)))

    def test_an_empty_fake_finds_nothing(self):
        """A fake with no products gives `None` for any id."""
        self.assertIsNone(run(FakeProductRepository().get_by_id(1)))

    def test_the_id_is_not_a_position(self):
        """The id is the key, not the place in a list: with the ids 10 and 20, `get_by_id(1)` finds nothing."""
        fake = make_fake(10, 20)
        self.assertIsNone(run(fake.get_by_id(1)))
        self.assertEqual(run(fake.get_by_id(20)).title, "Product 20")

    def test_it_does_not_change_the_fake(self):
        """Looking for a product does not add, remove or change anything."""
        fake = make_fake(1, 2)
        run(fake.get_by_id(2))
        run(fake.get_by_id(99))
        self.assertEqual(sorted(fake.products), [1, 2])


class FakeSearchTests(unittest.TestCase):
    """Task 2, `search`: ALL the products in a list, sorted by id. The query is ignored."""

    def test_it_gives_all_the_products_in_a_list(self):
        """The answer is a real `list` that holds the same product objects."""
        products = [make_product(id=1), make_product(id=2)]
        found = run(FakeProductRepository(products).search(ProductQuery()))
        self.assertIsInstance(found, list)
        self.assertEqual(len(found), 2)
        self.assertIs(found[0], products[0])
        self.assertIs(found[1], products[1])

    def test_an_empty_fake_gives_an_empty_list(self):
        """No products: an empty list (not `None`)."""
        self.assertEqual(run(FakeProductRepository().search(ProductQuery())), [])

    def test_the_products_are_sorted_by_id_not_by_the_order_they_came_in(self):
        """The fake is built with the ids 30, 2, 17, 5 (in that order). The answer is 2, 5, 17, 30."""
        found = run(make_fake(30, 2, 17, 5).search(ProductQuery()))
        self.assertEqual([p.id for p in found], [2, 5, 17, 30])

    def test_the_sort_is_by_id_and_not_by_title(self):
        """The titles are in the opposite order of the ids, so only a sort by id gives 1, 2, 3."""
        fake = FakeProductRepository([
            make_product(id=3, title="Apple"), make_product(id=1, title="Zebra"), make_product(id=2, title="Mango"),
        ])
        self.assertEqual([p.id for p in run(fake.search(ProductQuery()))], [1, 2, 3])

    def test_the_ids_are_sorted_as_numbers(self):
        """9 comes before 10 (as text, "10" would come before "9")."""
        found = run(make_fake(10, 9, 100, 2).search(ProductQuery()))
        self.assertEqual([p.id for p in found], [2, 9, 10, 100])

    def test_the_query_is_ignored(self):
        """Any query gives the same full list: a plain one, one that asks for 1 product, one with a keyword, even `None`.

        Anti-bypass: 12 products are saved, so a search that cuts the answer to the first 10 (the default `size`)
        or to the `size` of the query fails here.
        """
        fake = make_fake(*range(12, 0, -1))
        every_id = list(range(1, 13))
        queries = [ProductQuery(), ProductQuery(size=1), ProductQuery(page=3, size=2), ProductQuery(keyword="zzz"), None]
        for query in queries:
            with self.subTest(query=query):
                self.assertEqual([p.id for p in run(fake.search(query))], every_id)

    def test_the_answer_is_a_new_list_each_time(self):
        """Changing the list that came back does not change the fake."""
        fake = make_fake(1, 2, 3)
        found = run(fake.search(ProductQuery()))
        found.clear()
        self.assertEqual([p.id for p in run(fake.search(ProductQuery()))], [1, 2, 3])
        self.assertEqual(sorted(fake.products), [1, 2, 3])

    def test_it_does_not_change_the_fake(self):
        """Searching does not add or remove products, and does not reorder what the fake keeps."""
        fake = make_fake(3, 1, 2)
        run(fake.search(ProductQuery()))
        self.assertEqual(list(fake.products), [3, 1, 2])


class FakeAddTests(unittest.TestCase):
    """Task 2, `add`: the next id is the biggest id plus 1; the product is kept and given back."""

    def test_the_readme_table_for_the_next_id(self):
        """An empty fake gives 1. The ids 1 and 2 give 3. The ids 1 and 5 (a gap) give 6."""
        for ids, expected in [((), 1), ((1, 2), 3), ((1, 5), 6)]:
            with self.subTest(ids_before=ids):
                added = run(make_fake(*ids).add(make_product(title="New")))
                self.assertEqual(added.id, expected)

    def test_the_next_id_is_the_biggest_id_plus_one_whatever_the_order(self):
        """The biggest id counts, not the last one that came in and not how many products there are.

        Anti-bypass: `len(...) + 1` gives 4 for [7, 3, 1] (the biggest is 7, so the answer is 8), and the last
        id of [30, 2] is 2 (but the answer is 31).
        """
        cases = [((7, 3, 1), 8), ((30, 2), 31), ((2, 30), 31), ((100,), 101), ((1,), 2), ((50, 51, 3), 52)]
        for ids, expected in cases:
            with self.subTest(ids_before=ids):
                self.assertEqual(run(make_fake(*ids).add(make_product(title="New"))).id, expected)

    def test_add_gives_back_the_same_product_object(self):
        """The product that comes back is the very object that went in, now with its id filled in."""
        product = make_product(title="Lamp")
        self.assertIsNone(product.id)
        result = run(make_fake(1, 2).add(product))
        self.assertIs(result, product)
        self.assertEqual(product.id, 3)
        self.assertIsInstance(product.id, int)

    def test_the_product_is_kept_in_the_fake_under_its_id(self):
        """After `add`, the dictionary holds the product under its new id."""
        fake = make_fake(1, 5)
        product = run(fake.add(make_product(title="Lamp")))
        self.assertIs(fake.products[6], product)
        self.assertEqual(sorted(fake.products), [1, 5, 6])

    def test_an_added_product_can_be_found_again(self):
        """`get_by_id` finds the new product, and `search` lists it last (it has the biggest id)."""
        fake = make_fake(1, 5)
        product = run(fake.add(make_product(title="Lamp")))
        self.assertIs(run(fake.get_by_id(product.id)), product)
        self.assertEqual([p.id for p in run(fake.search(ProductQuery()))], [1, 5, 6])
        self.assertIs(run(fake.search(ProductQuery()))[-1], product)

    def test_the_other_products_are_not_touched(self):
        """The products that were there before keep their ids and their data."""
        fake = make_fake(1, 5)
        before = {i: snapshot(p) for i, p in fake.products.items()}
        run(fake.add(make_product(title="Lamp")))
        for product_id, values in before.items():
            self.assertEqual(snapshot(fake.products[product_id]), values)

    def test_adding_again_and_again_counts_up(self):
        """Three products added to an empty fake get the ids 1, 2, 3. Three more get 4, 5, 6."""
        fake = FakeProductRepository()
        ids = [run(fake.add(make_product(title=f"P{n}"))).id for n in range(6)]
        self.assertEqual(ids, [1, 2, 3, 4, 5, 6])
        self.assertEqual(len(fake.products), 6)

    def test_every_added_product_has_its_own_id(self):
        """Two products added one after the other never get the same id (the first one is not overwritten)."""
        fake = FakeProductRepository()
        first = run(fake.add(make_product(title="First")))
        second = run(fake.add(make_product(title="Second")))
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(run(fake.get_by_id(first.id)).title, "First")
        self.assertEqual(run(fake.get_by_id(second.id)).title, "Second")


class FakeIsolationTests(unittest.TestCase):
    """The rules of the README: each fake has its own dictionary, and the methods are `async def`."""

    def test_two_fakes_never_share_their_products(self):
        """A product added to one fake is not in the other. (A shared dictionary would make tests disturb each other.)"""
        first, second = FakeProductRepository(), FakeProductRepository()
        run(first.add(make_product(title="Only in the first")))
        self.assertIsNot(first.products, second.products)
        self.assertEqual(run(second.search(ProductQuery())), [])
        self.assertIsNone(run(second.get_by_id(1)))
        self.assertEqual(run(second.add(make_product(title="Probe"))).id, 1)

    def test_a_new_fake_starts_empty_even_after_another_one_was_used(self):
        """Create a fake, fill it, forget it. The next new fake is empty and starts again at the id 1."""
        used = FakeProductRepository()
        for n in range(3):
            run(used.add(make_product(title=f"P{n}")))
        fresh = FakeProductRepository()
        self.assertEqual(run(fresh.search(ProductQuery())), [])
        self.assertEqual(run(fresh.add(make_product(title="First"))).id, 1)

    def test_two_fakes_built_from_the_same_list_stay_apart(self):
        """The same list of products goes into two fakes. Adding to one leaves the other, and the list, unchanged."""
        shared_list = [make_product(id=1, title="One"), make_product(id=2, title="Two")]
        left, right = FakeProductRepository(shared_list), FakeProductRepository(shared_list)
        run(left.add(make_product(title="Three")))
        self.assertEqual(sorted(left.products), [1, 2, 3])
        self.assertEqual(sorted(right.products), [1, 2])
        self.assertEqual(len(shared_list), 2)

    def test_the_three_methods_are_async(self):
        """`get_by_id`, `search` and `add` are still `async def` (the service awaits them)."""
        for name in ("get_by_id", "search", "add"):
            with self.subTest(method=name):
                self.assertTrue(inspect.iscoroutinefunction(getattr(FakeProductRepository, name)), f"{name} must be async def")

    def test_the_constructor_still_takes_an_optional_list(self):
        """`FakeProductRepository()` and `FakeProductRepository([...])` both work, and the list is stored by id."""
        self.assertEqual(list(inspect.signature(FakeProductRepository).parameters), ["products"])
        self.assertEqual(FakeProductRepository().products, {})
        product = make_product(id=4)
        self.assertEqual(FakeProductRepository([product]).products, {4: product})


# ===========================================================================
# The fake used the way the tests of the course use it: through ProductService
# ===========================================================================

class ServiceWithTheFakeTests(unittest.TestCase):
    """`ProductService` works on the fake as it would on MySQL. This is what makes the service easy to test."""

    def test_get_by_id_gives_the_dictionary_of_the_product(self):
        """The service finds the product in the fake and returns `to_dict` of it: category name and low_stock included."""
        beauty = make_product(id=1, title="Lip Gloss", stock=3, category=Category(name="beauty"))
        mug = make_product(id=2, title="Mug", stock=40)
        service = ProductService(FakeProductRepository([beauty, mug]), FakeCategoryRepository())
        first, second = run(service.get_by_id(1)), run(service.get_by_id(2))
        self.assertEqual((first["title"], first["category"], first["low_stock"]), ("Lip Gloss", "beauty", True))
        self.assertEqual((second["title"], second["category"], second["low_stock"]), ("Mug", None, False))
        self.assertEqual(set(first), ALL_KEYS)

    def test_get_by_id_of_a_missing_product_raises_our_own_error(self):
        """The fake gives `None`, and the service turns it into `ProductNotFoundError` (status 404)."""
        service = make_service(1, 2)
        with self.assertRaises(ProductNotFoundError) as caught:
            run(service.get_by_id(99))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertIn("99", str(caught.exception))

    def test_list_products_gives_every_dictionary_sorted_by_id(self):
        """The list holds one dictionary per product, in the order of the ids."""
        service = make_service(30, 2, 17)
        listed = run(service.list_products(ProductQuery()))
        self.assertEqual([item["id"] for item in listed], [2, 17, 30])
        self.assertTrue(all(set(item) == ALL_KEYS for item in listed))

    def test_list_products_of_an_empty_fake_is_an_empty_list(self):
        """No products: an empty list."""
        self.assertEqual(run(make_service().list_products(ProductQuery())), [])

    def test_create_gives_the_next_id_and_the_category_name(self):
        """The README example: a product created in a fake that holds the ids 1 and 5 gets the id 6."""
        service = make_service(1, 5)
        data = ProductCreate(title="Toy Robot", price=Decimal("7.50"), stock=40, category="toys")
        created = run(service.create(data))
        self.assertEqual((created["id"], created["title"], created["category"]), (6, "Toy Robot", "toys"))
        self.assertEqual(created["price"], Decimal("7.50"))
        self.assertIs(created["low_stock"], False)

    def test_create_without_a_category_and_with_low_stock(self):
        """No category gives `None`; a stock of 10 gives `low_stock` True (10 is low)."""
        created = run(make_service().create(ProductCreate(title="Candle", price=Decimal("3.00"), stock=10)))
        self.assertEqual(created["id"], 1)
        self.assertIsNone(created["category"])
        self.assertIs(created["low_stock"], True)

    def test_a_created_product_can_be_read_again(self):
        """`create` and then `get_by_id` and `list_products` see the same product."""
        service = make_service(1, 2)
        created = run(service.create(ProductCreate(title="Candle", price=Decimal("3.00"), stock=4, category="home")))
        self.assertEqual(run(service.get_by_id(created["id"])), created)
        self.assertEqual([item["id"] for item in run(service.list_products(ProductQuery()))], [1, 2, 3])

    def test_two_creates_get_two_ids(self):
        """Two products created one after the other get the ids 1 and 2 in an empty fake."""
        service = make_service()
        first = run(service.create(ProductCreate(title="First", price=Decimal("1.00"), stock=1)))
        second = run(service.create(ProductCreate(title="Second", price=Decimal("2.00"), stock=2)))
        self.assertEqual((first["id"], second["id"]), (1, 2))

    def test_two_services_do_not_share_products(self):
        """A product created through one service is not seen through another service (each has its own fake)."""
        left, right = make_service(), make_service()
        run(left.create(ProductCreate(title="Only left", price=Decimal("1.00"), stock=1)))
        self.assertEqual(len(run(left.list_products(ProductQuery()))), 1)
        self.assertEqual(run(right.list_products(ProductQuery())), [])


# ===========================================================================
# Many random steps, checked against a plain dictionary
# ===========================================================================

class RandomStepsTests(unittest.TestCase):
    """Random scripts of `add`, `get_by_id` and `search`, checked against a plain dictionary kept by the test.

    Anti-bypass: the scripts are made by the test, so a fake that only knows the README examples fails.
    """

    def test_random_scripts_match_a_plain_dictionary(self):
        """40 scripts of 25 steps each. After every step the fake and the plain dictionary agree (the first step that differs is shown)."""
        generator = random.Random(11)
        for script in range(40):
            start_ids = generator.sample(range(1, 60), generator.randint(0, 6))
            fake = make_fake(*start_ids)
            model = {i: fake.products[i] for i in start_ids}
            for step in range(25):
                action = generator.choice(["add", "add", "get", "search"])
                where = f"script {script}, step {step} ({action}), the ids before: {sorted(model)}"
                if action == "add":
                    product = make_product(title=f"New {script}-{step}")
                    added = run(fake.add(product))
                    expected_id = max(model, default=0) + 1
                    model[expected_id] = product
                    self.assertIs(added, product, where)
                    self.assertEqual(added.id, expected_id, where)
                elif action == "get":
                    wanted = generator.randint(0, max(model, default=0) + 3)
                    self.assertIs(run(fake.get_by_id(wanted)), model.get(wanted), f"{where}, asked for id {wanted}")
                else:
                    found = run(fake.search(ProductQuery()))
                    self.assertEqual([p.id for p in found], sorted(model), where)


# ===========================================================================
# What must stay as it was
# ===========================================================================

class UntouchedFilesTests(unittest.TestCase):
    """The README says: do not modify the models, the schemas, `ProductService` or `FakeCategoryRepository`."""

    def test_the_fake_category_repository_is_as_it_was(self):
        """`get_or_create(name)` gives a new `Category` with that name."""
        category = run(FakeCategoryRepository().get_or_create("toys"))
        self.assertIsInstance(category, Category)
        self.assertEqual(category.name, "toys")

    def test_the_low_stock_limit_is_still_ten(self):
        """The constant is `10`: the rule changed to "10 is also low", the number did not."""
        self.assertEqual(LOW_STOCK_LIMIT, 10)

    def test_the_product_model_still_has_its_columns(self):
        """The table `product` has the columns that `to_dict` reads."""
        columns = set(Product.__table__.columns.keys())
        self.assertTrue({"id", "title", "description", "price", "stock", "image_url", "category_id"} <= columns)

    def test_the_service_still_receives_its_repositories(self):
        """`ProductService(repo, categories)` keeps its two parameters and its three async methods."""
        self.assertEqual(list(inspect.signature(ProductService).parameters), ["repo", "categories"])
        for name in ("get_by_id", "list_products", "create"):
            with self.subTest(method=name):
                self.assertTrue(inspect.iscoroutinefunction(getattr(ProductService, name)))


# ===========================================================================
# Run all tests
# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
