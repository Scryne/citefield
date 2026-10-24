from decimal import Decimal

import pytest

from citefield.verify.amounts import amount, iban_ok, luhn_ok, tckn_ok, vkn_ok


@pytest.mark.parametrize(
    "text,value",
    [
        ("23.000", Decimal("23000")),  # Indonesian thousands
        ("Rp 1.250.000", Decimal("1250000")),
        ("1,234.50", Decimal("1234.50")),
        ("1.234,50", Decimal("1234.50")),
        ("$12.00", Decimal("12.00")),
        ("1,5", Decimal("1.5")),
        ("45,500", Decimal("45500")),
        ("-3.00", Decimal("-3.00")),
        ("(3.00)", Decimal("-3.00")),
        ("1 234,50 €", Decimal("1234.50")),
        ("12.", Decimal("12")),
        ("TOTAL", None),
    ],
)
def test_amount(text, value):
    assert amount(text) == value


def test_iban():
    assert iban_ok("GB82 WEST 1234 5698 7654 32")
    assert iban_ok("TR330006100519786457841326")
    assert not iban_ok("GB82 WEST 1234 5698 7654 33")
    assert not iban_ok("not an iban")


def test_turkish_ids():
    assert tckn_ok("10000000146")
    assert not tckn_ok("10000000147") and not tckn_ok("00000000146") and not tckn_ok("123")
    # VKN: exactly one check digit is accepted for any 9-digit prefix. Not yet verified against a published VKN
    # (Roadmap Faz 4 note); until then a VKN failure is a review reason, never a rejection.
    for prefix in ("123456789", "000000001", "987654321"):
        assert sum(vkn_ok(prefix + c) for c in "0123456789") == 1


def test_luhn():
    assert luhn_ok("4539 1488 0343 6467") and not luhn_ok("4539 1488 0343 6468")
