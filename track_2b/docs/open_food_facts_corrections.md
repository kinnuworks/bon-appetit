# Contributing the energy corrections back to Open Food Facts

`eval/off_energy_flags.csv` lists 3,035 Swiss products whose printed energy disagrees with their own fat, carbohydrate and protein values. `eval/off_corrections_kj_as_kcal.csv` holds the 433 where the energy value is about 4.2 times too high, the signature of kilojoules typed into the kilocalorie field. Each row has a product link and the likely fix.

How to contribute them:

1. Create an Open Food Facts account and read their contribution guidelines.
2. Start with the kJ-as-kcal list. Open each product link, check the nutrition photo, and correct the value only when the photo confirms it.
3. For the wider list, share the CSV with the Open Food Facts community (their Slack or forum, Switzerland channel) as a quality report, so contributors with access to the products can review them.
4. Never change a value without the label photo; the rule finds inconsistencies, not the right answer.

The same check flags none of the 1,046 non-alcoholic foods in the federal FSVO database, so it does not fire at random.
