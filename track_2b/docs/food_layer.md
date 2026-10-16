# The food layer

The food layer is plain code that sits between Apertus and the numbers. It has three jobs.

## Food groups

FSVO categories map to the groups of the Swiss food pyramid published by the Swiss Society for Nutrition (SGE). The mapping is in `src/bonappetit/foodlayer.py` (`CATEGORY_TO_GROUP`). Non-alcoholic drinks are split: sweet drinks and juices count with sweets, water, tea and coffee are their own group and are not compared with a reference.

## Daily reference amounts

Grams per adult per day, derived from the SGE portion advice:

| Group | Portions | Reference |
|---|---|---|
| Vegetables and fruit | 5 × 120 g | 600 g |
| Grains, potatoes, legumes | 3 portions, mixed (bread 75 to 125 g, potatoes 180 to 300 g, dry pasta or rice 60 to 100 g) | 330 g |
| Milk and dairy | 3 portions (200 ml milk, 150 to 200 g yoghurt, 30 g hard cheese) | 450 g |
| Meat, fish, eggs, alternatives | 1 × 100 to 120 g | 110 g |
| Oils, fats, nuts | 2 to 3 tablespoons of oil plus 20 to 30 g nuts | 55 g |
| Sweets, snacks, sweet drinks | at most one small portion | 50 g |

These are a household guide, derived by hand from portion sizes, and stated as such in the app.

## Checks that veto a link

| Rule | Example it stops |
|---|---|
| Unit | A line sold in litres linked to a solid food (litres of cheese) |
| Pack | A pack above 25 kg |
| Energy (Atwater) | Printed kcal that disagree with 4·protein + 4·carbohydrate + 9·fat + 2·fibre by more than 25% and 25 kcal. Used to flag suspicious Open Food Facts entries |

When the unit rule rejects the model's pick, the linker takes the best-ranked candidate that passes, and the line is marked as overruled.

## Swiss food words

A short glossary (`HELVETISMS`) adds the standard name for Swiss and regional words that the 8B model misreads, such as Rüebli (carrot), Nüsslisalat (lamb's lettuce) and Peperoni (sweet pepper), plus common French and Italian food words. The glossary only adds search terms and a note to the model; it never decides a link.
