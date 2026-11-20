import re
from datetime import date

# Skompilowane wyrażenia regularne z grupami nazwanymi (?P<nazwa>...)
PESEL_RE: re.Pattern[str] = re.compile(
    r"^(?P<year>\d{2})(?P<month>\d{2})(?P<day>\d{2})(?P<serial>\d{3})(?P<gender>\d)(?P<checksum>\d)$"
)

EMAIL_RE: re.Pattern[str] = re.compile(
    r"^(?P<user>[a-zA-Z0-9._%+-]+)@(?P<domain>[a-zA-Z0-9.-]+)\.(?P<tld>[a-zA-Z]{2,})$"
)

PHONE_RE: re.Pattern[str] = re.compile(
    r"^(?:(?P<prefix>\+48|0048)[\s-]?)?(?P<number>[4-9]\d{2}[\s-]?\d{3}[\s-]?\d{3})$"
)

POSTAL_RE: re.Pattern[str] = re.compile(
    r"^(?P<region>\d{2})-(?P<district>\d{3})$"
)

PESEL_WEIGHTS: tuple[int, ...] = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)


def verify_pesel_checksum_and_date(pesel: str) -> tuple[bool, str | None]:
    """Sprawdza regex, sumę kontrolną PESEL oraz datę urodzenia. Zwraca (czy_poprawny, płeć)."""
    match = PESEL_RE.match(pesel)
    if not match:
        return False, None

    # Weryfikacja cyfry kontrolnej na podstawie wag PESEL
    digits = [int(ch) for ch in pesel]
    weighted_sum = sum(w * d for w, d in zip(PESEL_WEIGHTS, digits[:10]))
    expected_checksum = (10 - (weighted_sum % 10)) % 10
    if digits[10] != expected_checksum:
        return False, None

    year = int(match.group("year"))
    raw_month = int(match.group("month"))
    day = int(match.group("day"))

    # Dekodowanie stulecia zakodowanego w miesiącu numeru PESEL
    if 1 <= raw_month <= 12:
        full_year, month = 1900 + year, raw_month
    elif 21 <= raw_month <= 32:
        full_year, month = 2000 + year, raw_month - 20
    elif 41 <= raw_month <= 52:
        full_year, month = 2100 + year, raw_month - 40
    elif 61 <= raw_month <= 72:
        full_year, month = 2200 + year, raw_month - 60
    elif 81 <= raw_month <= 92:
        full_year, month = 1800 + year, raw_month - 80
    else:
        return False, None

    # Walidacja poprawności kalendarzowej daty (np. lata przestępne)
    try:
        date(full_year, month, day)
    except ValueError:
        return False, None

    gender = "K" if int(match.group("gender")) % 2 == 0 else "M"
    return True, gender