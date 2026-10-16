from bonappetit.foodlayer import atwater_kcal, check_energy, check_unit, group_for, helvetism_hints
from bonappetit.llm import conform


def test_groups():
    assert group_for("Milch und Milchprodukte/Käse") == "dairy"
    assert group_for("Alkoholfreie Getränke/Süssgetränke") == "sweets_snacks_drinks"
    assert group_for("Alkoholfreie Getränke/Wasser") == "drinks_unsweetened"


def test_atwater_and_energy_check():
    milk = {"energy_kcal": 65, "proteins": 3.3, "carbohydrates": 4.7, "fat": 3.6, "fiber": 0}
    assert abs(atwater_kcal(milk) - 65) < 1
    assert check_energy(milk).ok
    assert not check_energy({**milk, "energy_kcal": 400}).ok


def test_litres_of_cheese_are_rejected():
    assert not check_unit(line_is_volume=True, food_is_liquid=False, group="dairy").ok
    assert check_unit(line_is_volume=True, food_is_liquid=True, group="dairy").ok


def test_helvetisms():
    assert any("Karotte" in h for h in helvetism_hints("NATURAPLAN BIO RUEBLI 1KG"))
    assert helvetism_hints("BANANEN 1KG") == []


def test_conform_coerces_model_output():
    schema = {"properties": {"choice": {"type": "integer"}, "sure": {"type": "boolean"}}}
    assert conform({"choice": "3", "sure": "true", "extra": 1}, schema) == {"choice": 3, "sure": True}
    assert conform({}, schema) == {"choice": 0, "sure": False}
