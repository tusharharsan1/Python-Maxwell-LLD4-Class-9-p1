# A Fake Repository at ShopNest

> **Where the files are:** this branch holds the finished solution in the `solution/` folder: the finished code, and the tests in `solution/tests/`. Every path below (such as `app/`, `tests/` and `try_it.py`) is inside `solution/`. Open a terminal in `solution/` to run the commands. To run the tests, type `python -m unittest -v` (or `pytest`) there. The starter files with the TODO notes are on the `main` branch, in `base/`.

## Problem Statement
In class we made our product code **easy to test** in two ways. First, we pulled the shop rule (`low_stock`) and the dictionary building out of the service into a small **pure function**, `to_dict`: it needs no database and no server, so a test can call it in one line. Second, `ProductService` does not create its repository: it **receives** one, so a test can hand it a **fake repository**, a small class with the same methods that keeps a few products in a dictionary in memory. Now you finish both pieces. You need about 7 lines of code, in 2 small tasks.

## Requirements
### Task 1: the function `to_dict`
`to_dict(product)` turns one `Product` object into a dictionary for the client. Six keys are already written. You add the last two.

| Key | What it holds | Already written? |
|---|---|---|
| `id`, `title`, `description`, `price`, `stock`, `image_url` | copied from the product, as they are | **yes** |
| `category` | the **name** of the product's category (a text), or `None` when the product has no category | **no** (TODO 1) |
| `low_stock` | `True` when the stock is `LOW_STOCK_LIMIT` (10) **or fewer**, otherwise `False` | **no** (TODO 2) |

The product owner changed the rule: **10 left is also low**. So the edge of the rule is the number 10 itself.

| The stock | `low_stock` |
|---|---|
| `0` | `True` |
| `9` | `True` |
| `10` | `True` |
| `11` | `False` |

| The product | `category` |
|---|---|
| a product with `Category(name="beauty")` | `"beauty"` |
| a product with no category | `None` |

The rules for `to_dict`:
- It is a **pure** function: it uses only the product it receives. It does not change the product, and it does not touch a database.
- The dictionary has exactly these 8 keys.
- `price` stays a `Decimal`, exactly as it is in the product.

### Task 2: the class `FakeProductRepository`
The real repository asks MySQL. The fake one answers from a dictionary in memory (`self.products`, which maps an id to a product). The constructor is already written: it takes an optional list of products and puts each one in the dictionary by its id. You write three methods. The service awaits them, so they are `async def` (already written).

| Method | What it does | Already written? |
|---|---|---|
| `get_by_id(product_id)` | gives back the product with that id, or `None` when there is none | **no** (TODO 3) |
| `search(query)` | gives back **all** the products in a list, sorted by their ids. The query is ignored | **no** (TODO 4) |
| `add(product)` | gives the product the **next id**, keeps it in the fake, and gives the product back | **no** (TODO 5) |

How `add` chooses the id: take the biggest id in the fake and add 1. A fake with no products gives the id `1`.

| The ids in the fake before `add` | The id that `add` gives |
|---|---|
| none (an empty fake) | `1` |
| `1` and `2` | `3` |
| `1` and `5` (there is a gap) | `6` |

The rules for `FakeProductRepository`:
- Each fake has **its own** dictionary. Two fakes never share their products, so one test cannot disturb another.
- `add` gives back the **same product object** that it received, with its `id` now filled in.
- A product that was added can be found again with `get_by_id`, and it shows up in `search`.

To achieve these requirements we need to do 2 things:
- **Task 1:** finish `to_dict`: the `category` key and the `low_stock` key.
- **Task 2:** finish the three methods of `FakeProductRepository`.

## Instructions
1. Open `app/services/product_mapper.py`. We need to finish the function `to_dict`. It has two TODO notes (`TODO 1` and `TODO 2`): the keys `category` and `low_stock`.
2. Open `app/fakes.py`. We need to finish the class `FakeProductRepository`. It has three TODO notes (`TODO 3` to `TODO 5`): `get_by_id`, `search` and `add`. The class `FakeCategoryRepository` above it is already finished: it is your example of a fake.
3. Do not modify the models, the schemas, `ProductService`, `FakeCategoryRepository`, the constructor of `FakeProductRepository`, or the names of the functions and their parameters. Feel free to add new functions if required.
4. When a TODO in `fakes.py` is finished, delete the `...` line under it.
5. Run `python try_it.py` from this folder (the one that contains `app/` and `try_it.py`) to see what your code does. When both tasks are finished, you should see exactly this:
   ```
   Task 1: to_dict
     title and price               : Lip Gloss 5.00
     category name                 : beauty
     no category                   : None
     low_stock for 9               : True
     low_stock for 10              : True
     low_stock for 11              : False
   Task 2: FakeProductRepository
     get_by_id(1)                  : Lip Gloss
     get_by_id(99)                 : None
     search                        : Lip Gloss, Mug
     add: the next id              : 3
     add: first on an empty shelf  : 1
     the service, get              : Lip Gloss low_stock=True
     the service, list             : Lip Gloss, Mug
     the service, create           : id 3, category toys
   ```
   Before you start, `try_it.py` already runs: it shows `something is wrong -> ...` on the lines that need your code, with the name of the error.
6. Your code will be checked with the test file `tests/test_fake_repository.py`. It checks the cases in the Requirements above and the rules. While you write your code, use `python try_it.py` (instruction 5) to check your work.
7. You do not need MySQL, a server, an internet connection, a key or `pytest` for this assignment. The `Product` objects live only in memory, and nothing is saved. `sqlalchemy` and `pydantic` are already installed (Classes 4 and 7). It works with Python 3.8 or newer.
8. Hints (all of these use ideas from class):
   - **The category name (TODO 1).** A product with no category has `product.category` equal to `None`, and `None` has no `.name`, so choose first:
     ```python
     "category": product.category.name if product.category else None,
     ```
   - **Low stock (TODO 2).** One comparison with the constant that is already in the file. Remember: 10 is low, so it is "less than or equal":
     ```python
     "low_stock": product.stock <= LOW_STOCK_LIMIT,
     ```
   - **Find by id (TODO 3).** A dictionary has a method that gives `None` instead of an error when the key is missing:
     ```python
     return self.products.get(product_id)
     ```
   - **All the products, sorted (TODO 4).**
     ```python
     return sorted(self.products.values(), key=lambda p: p.id)
     ```
   - **Add with the next id (TODO 5).** Three lines. `max(self.products, default=0)` gives the biggest id, and gives `0` when the dictionary is empty:
     ```python
     product.id = max(self.products, default=0) + 1
     self.products[product.id] = product
     return product
     ```
   - **If something looks wrong.** `KeyError: 'category'` or `KeyError: 'low_stock'` on the first lines means a key is still missing in `to_dict`. If `low_stock for 10` shows `False`, you wrote `<` and not `<=`. If `get_by_id(1)` or `add` shows `'NoneType' object has no attribute ...`, a method still has its `...` line or is missing the `return`. If `add: first on an empty shelf` shows a `ValueError` from `max`, the `default=0` is missing. If `search` shows the products in the wrong order, they must be sorted by `id`.
