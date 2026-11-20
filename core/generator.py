import random
from collections.abc import Iterator
from datetime import date, timedelta

from core.patterns import PESEL_WEIGHTS
from utils.decorators import validate_record_limit

FIRST_NAMES_M = ("Jan", "Piotr", "Krzysztof", "Tomasz", "Paweł", "Michał", "Marcin", "Jakub", "Adam", "Łukasz")
FIRST_NAMES_F = ("Anna", "Maria", "Katarzyna", "Małgorzata", "Agnieszka", "Barbara", "Ewa", "Magdalena", "Elżbieta", "Joanna")
LAST_NAMES = ("Nowak", "Kowalski", "Wiśniewski", "Wójcik", "Kowalczyk", "Kamiński", "Lewandowski", "Zieliński", "Szymański", "Woźniak")
DOMAINS = ("gmail.com", "wp.pl", "onet.pl", "interia.pl", "outlook.com", "firma.pl")


def generate_valid_pesel(rng: random.Random, is_female: bool) -> str:
    """Generuje poprawny matematycznie numer PESEL dla losowej daty z lat 1950–2008."""
    start_date = date(1950, 1, 1)
    random_days = rng.randint(0, 58 * 365)
    birth = start_date + timedelta(days=random_days)

    yy = birth.year % 100
    mm = birth.month + (20 if birth.year >= 2000 else 0)
    dd = birth.day

    serial = rng.randint(0, 999)
    gender_digit = rng.choice((0, 2, 4, 6, 8)) if is_female else rng.choice((1, 3, 5, 7, 9))

    base = f"{yy:02d}{mm:02d}{dd:02d}{serial:03d}{gender_digit}"
    digits = [int(c) for c in base]
    weighted_sum = sum(w * d for w, d in zip(PESEL_WEIGHTS, digits))
    checksum = (10 - (weighted_sum % 10)) % 10
    return f"{base}{checksum}"


def infinite_valid_person_stream(seed: int = 42) -> Iterator[dict[str, str]]:
    """Nieskończony generator poprawnych rekordów danych osobowych (yield)."""
    rng = random.Random(seed)
    while True:
        is_female = rng.choice((True, False))
        first_name = rng.choice(FIRST_NAMES_F if is_female else FIRST_NAMES_M)
        last_name = rng.choice(LAST_NAMES)
        if is_female and last_name.endswith("ski"):
            last_name = last_name[:-1] + "a"

        pesel = generate_valid_pesel(rng, is_female)
        slug = f"{first_name.lower()}.{last_name.lower()}{rng.randint(1, 999)}"
        slug = (
            slug.replace("ł", "l")
            .replace("ą", "a")
            .replace("ę", "e")
            .replace("ś", "s")
            .replace("ć", "c")
            .replace("ż", "z")
            .replace("ź", "z")
            .replace("ń", "n")
            .replace("ó", "o")
        )

        yield {
            "first_name": first_name,
            "last_name": last_name,
            "pesel": pesel,
            "email": f"{slug}@{rng.choice(DOMAINS)}",
            "phone": f"+48 {rng.randint(500, 889)} {rng.randint(100, 999)} {rng.randint(100, 999)}",
            "postal_code": f"{rng.randint(0, 99):02d}-{rng.randint(0, 999):03d}",
        }


@validate_record_limit(min_records=1, max_records=5_000_000)
def person_stream_with_errors(limit: int, error_rate: float = 0.1, seed: int = 42) -> Iterator[dict[str, str]]:
    """
    Strumień generujący dokładnie 'limit' rekordów, delegujący do nieskończonego generatora
    przez 'yield from' i celowo uszkadzający zadany odsetek rekordów.
    """
    rng = random.Random(seed + 1)

    def _corrupted_pipeline() -> Iterator[dict[str, str]]:
        stream = infinite_valid_person_stream(seed=seed)
        for _ in range(limit):
            record = next(stream)
            if rng.random() < error_rate:
                corrupt_field = rng.choice(("pesel", "email", "phone", "postal_code"))
                if corrupt_field == "pesel":
                    # Zmieniamy ostatnią cyfrę sumy kontrolnej na niepoprawną
                    last_digit = (int(record["pesel"][-1]) + 1) % 10
                    record["pesel"] = record["pesel"][:-1] + str(last_digit)
                elif corrupt_field == "email":
                    record["email"] = record["email"].replace("@", "_at_")
                elif corrupt_field == "phone":
                    record["phone"] = "123-abc"
                elif corrupt_field == "postal_code":
                    record["postal_code"] = "00000"
            yield record

    yield from _corrupted_pipeline()


def filter_pesel_prefix_stream(records: Iterator[dict[str, str]], year_prefix: str) -> Iterator[dict[str, str]]:
    """Wyrażenie generujące filtrujące leniwie strumień po prefiksie roku urodzenia w PESEL."""
    return (rec for rec in records if rec["pesel"].startswith(year_prefix))