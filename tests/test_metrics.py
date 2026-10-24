"""The measurer is tested against deliberately broken outputs before any number from it is trusted."""

import random

import pytest

from citefield.eval.metrics import Gold, Pred, match, summarize, values_equal

KINDS = {"item.name": "text", "item.count": "count", "item.price": "amount", "total": "amount"}


def kind_of(field: str) -> str:
    return KINDS[field]


def _documents(n: int = 20, seed: int = 0) -> list[list[Gold]]:
    rng = random.Random(seed)
    docs = []
    for _ in range(n):
        gold, y = [], 20.0
        for _ in range(rng.randint(2, 6)):
            price = f"{rng.randint(1, 99)},{rng.randint(0, 9)}00"
            gold += [
                Gold("item.name", rng.choice(["Tea", "Rice", "Soup", "Cake"]), (10, y, 120, y + 18)),
                Gold("item.count", "1", (130, y, 140, y + 18)),  # repeats on every line, on purpose
                Gold("item.price", price, (200, y, 260, y + 18)),
            ]
            y += 30
        gold.append(Gold("total", "99,000", (200, y + 10, 260, y + 28)))
        docs.append(gold)
    return docs


def _score(docs, corrupt) -> dict:
    ms = []
    for i, gold in enumerate(docs):
        ms += match(gold, corrupt(i, gold), kind_of)
    return summarize(ms).__dict__


DOCS = _documents()


def test_own_labels_score_perfect():
    s = _score(DOCS, lambda i, g: [Pred(x.field, x.value, x.box) for x in g])
    assert s["value_rate"] == s["location_iou"] == s["location_center"] == 1.0


def test_boxes_from_another_document_score_near_zero():
    rng = random.Random(1)
    s = _score(DOCS, lambda i, g: [Pred(x.field, x.value, rng.choice(DOCS[(i + 7) % len(DOCS)]).box) for x in g])
    assert s["value_rate"] == 1.0
    assert s["location_center"] < 0.15 and s["location_iou"] < 0.15, s


def test_shifted_boxes_drop():
    s = _score(DOCS, lambda i, g: [Pred(x.field, x.value, tuple(c + 30 for c in x.box)) for x in g])
    assert s["location_center"] < 1 and s["location_iou"] < 1


def test_wrong_values_score_zero():
    s = _score(DOCS, lambda i, g: [Pred(x.field, x.value + "7", x.box) for x in g])
    assert s["value_correct"] == 0


def test_repeated_value_is_not_cross_matched():
    """Predictions in reverse order must still pair each repeated "1" with its own line."""
    s = _score(DOCS, lambda i, g: [Pred(x.field, x.value, x.box) for x in reversed(g)])
    assert s["location_center"] == 1.0


def test_one_prediction_cannot_satisfy_two_labels():
    """A reader that emits the repeated "1" once must not get credit for every line."""

    def once(i, g):
        seen, out = set(), []
        for x in g:
            if (x.field, x.value) not in seen:
                seen.add((x.field, x.value))
                out.append(Pred(x.field, x.value, x.box))
        return out

    assert _score(DOCS, once)["value_rate"] < 1.0


def test_missing_box_counts_as_wrong_location():
    s = _score(DOCS, lambda i, g: [Pred(x.field, x.value, None) for x in g])
    assert s["value_rate"] == 1.0 and s["location_center"] == 0.0


@pytest.mark.parametrize(
    "kind,pred,gold,ok",
    [
        ("count", "1", "1Prs", True),
        ("count", "1", "1x", True),
        ("count", "2", "1x", False),
        ("amount", "23000", "23.000", True),
        ("amount", "23,000", "Rp 23.000", True),
        ("amount", "TOTAL", "23.000", False),
        ("text", "Ice Tea", "ICE TEA", True),
        ("text", "Ice", "Ice Tea", False),
    ],
)
def test_values_equal(kind, pred, gold, ok):
    assert values_equal(kind, pred, gold) is ok


def test_containment_only_when_asked():
    assert values_equal("id", "INV-0042", "Invoice No: INV-0042", containment=True)
    assert not values_equal("id", "INV-0042", "Invoice No: INV-0042")
    assert not values_equal("id", "42", "Invoice No: INV-0042", containment=True)  # too short to trust
