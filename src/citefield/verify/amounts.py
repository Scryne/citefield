"""Printed amounts and check digits.

Amounts are parsed without a locale: the last separator is a decimal point only when one or two digits follow it.
"23.000" (Indonesian thousands), "1,234.50" and "1.234,50" all parse; "1,5" is 1.5.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_NUMBER = re.compile(r"-?\d[\d.,' ]*")


def amount(text: str) -> Decimal | None:
    m = _NUMBER.search(text.replace(" ", " "))
    if not m:
        return None
    raw = m.group(0).strip().rstrip(".,' ")
    negative = raw.startswith("-") or bool(re.search(r"\(\s*\d", text))
    raw = raw.lstrip("-")
    seps = [i for i, ch in enumerate(raw) if ch in ".,"]
    if seps and 1 <= len(raw) - seps[-1] - 1 <= 2:
        whole, frac = raw[: seps[-1]], raw[seps[-1] + 1 :]
    else:
        whole, frac = raw, ""
    digits = re.sub(r"\D", "", whole)
    if not digits:
        return None
    try:
        value = Decimal(f"{digits}.{frac}" if frac else digits)
    except InvalidOperation:
        return None
    return -value if negative else value


def iban_ok(text: str) -> bool:
    s = re.sub(r"\s", "", text).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s):
        return False
    moved = s[4:] + s[:4]
    return int("".join(str(int(ch, 36)) for ch in moved)) % 97 == 1


def tckn_ok(text: str) -> bool:
    """Turkish national id: 11 digits, first non-zero, two check digits."""
    d = [int(c) for c in re.sub(r"\D", "", text)]
    if len(d) != 11 or d[0] == 0:
        return False
    if ((sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10) != d[9]:
        return False
    return sum(d[:10]) % 10 == d[10]


def vkn_ok(text: str) -> bool:
    """Turkish tax number: 10 digits, last one a check digit."""
    d = [int(c) for c in re.sub(r"\D", "", text)]
    if len(d) != 10:
        return False
    total = 0
    for i in range(9):
        t = (d[i] + 9 - i) % 10
        v = (t * 2 ** (9 - i)) % 9
        if t != 0 and v == 0:
            v = 9
        total += v
    return (10 - total % 10) % 10 == d[9]


def luhn_ok(text: str) -> bool:
    d = [int(c) for c in re.sub(r"\D", "", text)]
    if len(d) < 2:
        return False
    total = 0
    for i, n in enumerate(reversed(d)):
        if i % 2:
            n *= 2
            n -= 9 if n > 9 else 0
        total += n
    return total % 10 == 0


CHECKS = {"iban": iban_ok, "tckn": tckn_ok, "vkn": vkn_ok, "luhn": luhn_ok}
