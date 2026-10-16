from bonappetit.receipt import make_line, parse_pack, parse_text


def test_pack_sizes():
    assert parse_pack("M-BUDG VOLLMILCH UHT 1L") == (1000, True)
    assert parse_pack("RIVELLA ROT 6X1.5L") == (9000, True)
    assert parse_pack("QP GRUY.RAPE 200G") == (200, False)
    assert parse_pack("BANANEN 1,2KG") == (1200, False)
    assert parse_pack("APFEL") == (None, False)


def test_price_and_quantity():
    line = make_line("2 x LAIT ENTIER PAST. 1L 1.75")
    assert line.qty == 2 and line.price == 1.75 and line.text == "LAIT ENTIER PAST. 1L"


def test_nonfood_hint():
    assert make_line("TRAGTASCHE 0.30").nonfood_hint
    assert not make_line("BANANEN 1KG 2.40").nonfood_hint


def test_parse_text_skips_noise():
    lines = parse_text("MIGROS\n----\nBANANEN 1KG 2.40\n12.10.26 18:03\n")
    assert [l.text for l in lines] == ["MIGROS", "BANANEN 1KG"]
