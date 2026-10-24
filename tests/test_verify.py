from citefield.extract import Extracted, Extraction
from citefield.schema import load, parse
from citefield.verify import same_value, verify

RECEIPT = load("receipt")


def E(field, value, item=None, *, confidence=0.99, evidence=(), citation="exact"):
    ev = tuple(evidence) or (hash((field, value, item)) % 10**6 + 10**6,)  # distinct words unless given
    return Extracted(field, value, item, confidence, ev, ev, citation, (0, 0, 1, 1), 0)


def clean_receipt():
    return [
        E("item.name", "LATTE", 1),
        E("item.total", "4.50", 1),
        E("item.name", "MUFFIN", 2),
        E("item.total", "3.00", 2),
        E("subtotal", "7.50"),
        E("tax", "0.60"),
        E("total", "8.10"),
        E("tendered", "10.00"),
        E("change", "1.90"),
    ]


def second_of(fields):
    return [Extracted(f.field, f.value, f.item) for f in fields]


def test_a_consistent_receipt_is_approved_automatically():
    fields = clean_receipt()
    v = verify(Extraction(fields, second_of(fields)), RECEIPT)
    assert [d.status for d in v.decisions] == ["auto"] * len(fields), [d.reasons for d in v.decisions]
    assert {r.outcome for r in v.rules} == {"holds", "skipped"}  # product skipped: no quantities printed
    assert v.auto_share == 1.0 and v.possibly_missed == []


def test_second_read_disagreement_sends_only_that_field_to_review():
    fields = clean_receipt()
    second = second_of(fields)
    second[6] = Extracted("total", "8.70")  # image-only read sees 8.70
    v = verify(Extraction(fields, second), RECEIPT)
    assert v.decisions[6].status == "review" and "second read" in v.decisions[6].reasons[0]
    assert sum(d.status == "review" for d in v.decisions) == 1
    assert [m.value for m in v.possibly_missed] == ["8.70"]


def test_amounts_agree_across_formats():
    assert same_value("amount", "12.00", "12") and same_value("amount", "Rp 23.000", "23,000")
    assert not same_value("amount", "12.00", "12.80")
    assert same_value("count", "1x", "1") and same_value("text", "Ice Tea", "ICE TEA")


def test_failed_sum_flags_every_field_in_it():
    fields = clean_receipt()
    fields[3] = E("item.total", "3.50", 2)  # misread: items now add up to 8.00, not 7.50
    v = verify(Extraction(fields, second_of(fields)), RECEIPT)
    flagged = {fields[i].field + str(fields[i].item) for i, d in enumerate(v.decisions) if d.status == "review"}
    assert flagged == {"item.total1", "item.total2", "subtotalNone"}
    assert any(r.outcome == "fails" and r.detail == "8 != 7.5" for r in v.rules)


def test_change_rule_and_tolerance():
    fields = clean_receipt()
    fields[8] = E("change", "1.91")  # 10.00 - 8.10 = 1.90; off by a cent is within tolerance
    assert all(d.status == "auto" for d in verify(Extraction(fields, second_of(fields)), RECEIPT).decisions)
    fields[8] = E("change", "1.99")
    v = verify(Extraction(fields, second_of(fields)), RECEIPT)
    assert v.decisions[8].status == "review" and v.decisions[7].status == "review"


def test_product_rule_per_item():
    fields = [
        E("item.name", "TEA", 1),
        E("item.quantity", "2", 1),
        E("item.unit_price", "2.25", 1),
        E("item.total", "4.60", 1),
    ]
    v = verify(Extraction(fields, second_of(fields)), RECEIPT)
    assert [d.status for d in v.decisions] == ["auto", "review", "review", "review"]


def test_low_confidence_and_citation_triggers():
    fields = [
        E("total", "8.10", confidence=0.5),
        E("subtotal", "7.50", citation="outside"),
        E("tax", "0.60", citation="missing"),
        E("merchant", "COFFEE HOUSE", citation="partial"),
        E("tendered", "10.00", confidence=None),
    ]
    v = verify(Extraction(fields, second_of(fields)), RECEIPT)
    reasons = [" | ".join(d.reasons) for d in v.decisions]
    assert "confidence 0.50" in reasons[0]
    assert "do not contain" in reasons[1] and "no words cited" in reasons[2] and "only part" in reasons[3]
    assert v.decisions[4].status == "auto"  # no confidence given is not a reason by itself


def test_the_same_words_cited_for_two_roles():
    """S2b: the card payment cited both as card amount and as cash tendered."""
    fields = clean_receipt()
    fields[7] = E("tendered", "8.10", evidence=[42])
    fields[6] = E("total", "8.10", evidence=[42])
    v = verify(Extraction(fields, second_of(fields)), RECEIPT)
    assert "also cited as tendered" in " ".join(v.decisions[6].reasons)
    assert "also cited as total" in " ".join(v.decisions[7].reasons)


def test_missing_second_read_reviews_everything():
    fields = clean_receipt()
    v = verify(Extraction(fields, []), RECEIPT)
    assert all(d.status == "review" for d in v.decisions)


def test_check_digit():
    schema = parse({"fields": [{"name": "iban", "kind": "id", "check": "iban"}]})
    good = [E("iban", "GB82 WEST 1234 5698 7654 32")]
    bad = [E("iban", "GB82 WEST 1234 5698 7654 33")]
    assert verify(Extraction(good, second_of(good)), schema).decisions[0].status == "auto"
    assert "IBAN check digit" in verify(Extraction(bad, second_of(bad)), schema).decisions[0].reasons[0]


def test_a_rule_without_its_first_term_is_skipped_not_failed():
    fields = [f for f in clean_receipt() if f.field != "subtotal"]  # tax alone must not be compared with total
    v = verify(Extraction(fields, second_of(fields)), RECEIPT)
    assert all(d.status == "auto" for d in v.decisions), [d.reasons for d in v.decisions]
    assert any(r.rule.startswith("subtotal + tax") and r.outcome == "skipped" for r in v.rules)


def test_tax_inclusive_line_prices_may_add_up_to_the_total():
    """CORD: line prices include tax, the subtotal is printed before tax."""
    fields = [
        E("item.name", "TEA", 1),
        E("item.total", "11,000", 1),
        E("subtotal", "10,000"),
        E("tax", "1,000"),
        E("total", "11,000"),
    ]
    v = verify(Extraction(fields, second_of(fields)), RECEIPT)
    assert all(d.status == "auto" for d in v.decisions), [d.reasons for d in v.decisions]
