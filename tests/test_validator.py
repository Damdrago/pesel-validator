import pytest

from core.generator import filter_pesel_prefix_stream, person_stream_with_errors
from core.iterator import BatchIterator
from core.models import PersonRecord
from core.patterns import EMAIL_RE, PHONE_RE, POSTAL_RE, verify_pesel_checksum_and_date
from utils.decorators import validate_record_limit


def test_valid_pesel_verification() -> None:
    is_valid, gender = verify_pesel_checksum_and_date("44051401359")
    assert is_valid is True
    assert gender == "M"


def test_invalid_pesel_checksum() -> None:
    is_valid, gender = verify_pesel_checksum_and_date("44051401350")
    assert is_valid is False
    assert gender is None


def test_regex_patterns_named_groups() -> None:
    email_match = EMAIL_RE.match("jan.kowalski@firma.pl")
    assert email_match is not None
    assert email_match.group("user") == "jan.kowalski"
    assert email_match.group("domain") == "firma"
    assert email_match.group("tld") == "pl"

    phone_match = PHONE_RE.match("+48 501 234 567")
    assert phone_match is not None
    assert phone_match.group("prefix") == "+48"

    postal_match = POSTAL_RE.match("50-001")
    assert postal_match is not None
    assert postal_match.group("region") == "50"


def test_person_record_property_setter_and_method_decorator() -> None:
    record = PersonRecord(
        first_name="Anna",
        last_name="Nowak",
        pesel="44051401350",  # błędny PESEL
        email="anna@wp.pl",
        phone="501234567",
        postal_code="50-100",
    )
    assert record.is_valid is False

    # Próba wywołania metody chronionej dekoratorem @require_verified_state powinna rzucić PermissionError
    with pytest.raises(PermissionError):
        record.to_export_row()

    # Naprawienie PESEL przez setter @pesel.setter automatycznie rewaliduje obiekt
    record.pesel = "44051401359"
    assert record.is_valid is True
    exported = record.to_export_row()
    assert exported["gender"] == "M"


def test_batch_iterator_splits_stream() -> None:
    stream = person_stream_with_errors(limit=25, error_rate=0.0)
    batches = list(BatchIterator(stream, batch_size=10))
    assert len(batches) == 3
    assert [len(b) for b in batches] == [10, 10, 5]


def test_generator_expression_filter() -> None:
    records = [
        {"pesel": "90010112345"},
        {"pesel": "85050512345"},
        {"pesel": "90121212345"},
    ]
    filtered = list(filter_pesel_prefix_stream(iter(records), "90"))
    assert len(filtered) == 2


def test_parameterized_decorator_limit_validation() -> None:
    @validate_record_limit(min_records=5, max_records=100)
    def dummy_gen(limit: int) -> int:
        return limit

    assert dummy_gen(limit=50) == 50
    with pytest.raises(ValueError):
        dummy_gen(limit=500)