"""Pull the Swiss subset of Open Food Facts (ODbL) with printed nutrition values.

Run at build time; the output stays out of git (see .gitignore). Only barcodes and
our own annotations are redistributed.
"""
import sys
import duckdb

import os
URL = os.environ.get("OFF_PARQUET", "https://huggingface.co/datasets/openfoodfacts/product-database/resolve/main/food.parquet")
OUT = sys.argv[1] if len(sys.argv) > 1 else "data/off_ch.parquet"

NUTRIENTS = ["energy-kcal", "fat", "saturated-fat", "carbohydrates", "sugars", "fiber", "proteins", "salt"]
cols = ",\n".join(
    f"list_extract(list_transform(list_filter(nutriments, x -> x.name = '{n}'), x -> x.\"100g\"), 1) AS \"{n.replace('-', '_')}\""
    for n in NUTRIENTS
)

con = duckdb.connect()
con.sql("INSTALL httpfs; LOAD httpfs; SET enable_progress_bar=false;")
con.sql(f"""
COPY (
  SELECT code, brands, quantity, product_quantity, nova_group, nutriscore_grade,
         categories_tags, food_groups_tags, stores, lang,
         product_name,
         {cols}
  FROM read_parquet('{URL}')
  WHERE list_contains(countries_tags, 'en:switzerland')
    AND NOT coalesce(no_nutrition_data, false)
    AND len(product_name) > 0
) TO '{OUT}' (FORMAT parquet)
""")
n = con.sql(f"SELECT count(*), count(energy_kcal), count(sugars) FROM '{OUT}'").fetchone()
print("rows", n)
