# API Integration Test Design

The API tests use real FastAPI routes, Pydantic validation, SQLAlchemy models, an isolated SQLite database, and the real Product -> DishIngredient -> Dish relationships.

## Equivalence Partitioning

- Valid products.
- Products with invalid categories.
- Products with negative nutrients.
- Products where protein + fat + carbs is greater than 100.
- Dishes with existing products.
- Dishes with a missing product.
- Search requests with matches and without matches.
- Deleting a product without links and deleting a product used by a dish.
- Missing required product fields and missing required dish fields.
- Dish category macros in the name and explicit category override.
- Dish photo sources as uploaded images, links, and combined upload/link batches.
- Manual correction of dish nutrition values after the automatic nutrition draft.

## Boundary Value Analysis

- `protein + fat + carbs = 100` is valid.
- `protein + fat + carbs = 100.01` is invalid.
- `protein`, `fat`, `carbs = 0` are valid.
- `protein`, `fat`, `carbs = -0.01` are invalid.
- `quantity_grams = 0` is invalid.
- `quantity_grams = 0.01` is valid.
- `portion_size_grams = 0` is invalid.
- `portion_size_grams = 0.01` is valid.
- `photo_links` or uploaded `photos = 5` is valid.
- `photo_links` or uploaded `photos = 6` is invalid.
- Combined dish uploaded photos and `photo_links` greater than 5 is invalid.
- Product or dish name length of 1 is invalid, length of 2 is valid.

## Requirement Traceability Notes

- Product CRUD is covered through real `/products` routes, including validation, filters, search, sorting, detail, update, and protected delete when a product is linked to a dish.
- Dish CRUD is covered through real `/dishes` routes, including Product -> DishIngredient -> Dish persistence, filters, search, sorting, detail, update, and delete.
- Dish category macros are covered for every configured macro, for explicit category override, and for multiple macros where the first macro determines the category.
- Automatic nutrition calculation is covered through `/dishes/nutrition-draft`; creation tests also verify that draft values can be manually corrected by the user.
- Diet flag availability is covered on dish creation and ingredient replacement, including automatic removal of unavailable requested flags.

The same classes are reflected in `pytest.mark.parametrize` cases with readable ids, so the test report exposes the selected partitions and boundaries.
