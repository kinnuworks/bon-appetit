# How evaluation receipt lines are made

No licensed corpus of Swiss receipt lines exists, so `eval/build_set.py` turns real product names into receipt-style lines with these rules, in order:

1. Prefix the first brand when the name does not already contain it.
2. Replace shop brands with till shorthand: M-Budget → M-BUDG, M-Classic → M-CL, Prix Garantie → PRIX GAR., Qualité & Prix → QP, Naturaplan → NATURAPL., Betty Bossi → B.BOSSI, Anna's Best → ANNAS B., Sélection → SEL.
3. Remove accents and write in upper case.
4. Cut words longer than nine letters to seven letters plus a dot.
5. Keep the first 24 characters.
6. Append the pack size when it is a clean amount (500G, 1L).

The rules are inferred from the way Swiss tills shorten names; they are not measured on real receipts. Results are reported with that limit.
