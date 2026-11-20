import hashlib
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass

from core.models import PersonRecord


@dataclass(slots=True)
class BatchValidationResult:
    """Wynik walidacji pojedynczej paczki rekordów."""

    valid_rows: list[dict[str, str]]
    invalid_rows: list[dict[str, str]]


def validate_batch_worker(batch: list[dict[str, str]]) -> BatchValidationResult:
    """
    Funkcja robocza (CPU-bound) przetwarzająca pojedynczą paczkę rekordów:
    - sprawdza wzorce regex i sumę kontrolną PESEL poprzez model PersonRecord,
    - oblicza skrót kontrolny SHA-256 dla każdego poprawnego rekordu.
    """
    valid_rows: list[dict[str, str]] = []
    invalid_rows: list[dict[str, str]] = []

    for raw in batch:
        record = PersonRecord.from_dict(raw)
        if record.is_valid:
            row = record.to_export_row()
            # Dociążenie CPU-bound: wyliczenie kryptograficznego skrótu kontrolnego rekordu
            payload = f"{row['pesel']}|{row['email']}|{row['phone']}".encode("utf-8")
            row["record_hash"] = hashlib.sha256(payload).hexdigest()[:16]
            valid_rows.append(row)
        else:
            invalid_entry = dict(raw)
            invalid_entry["errors"] = ",".join(record.validation_errors)
            invalid_rows.append(invalid_entry)

    return BatchValidationResult(valid_rows=valid_rows, invalid_rows=invalid_rows)


def validate_batches_sequential(batches: list[list[dict[str, str]]]) -> list[BatchValidationResult]:
    """Waliduje wszystkie paczki sekwencyjnie w jednym wątku."""
    return [validate_batch_worker(batch) for batch in batches]


def validate_batches_threads(batches: list[list[dict[str, str]]], workers: int = 4) -> list[BatchValidationResult]:
    """Waliduje paczki współbieżnie z użyciem puli wątków (ograniczone przez GIL)."""
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(validate_batch_worker, batches))


def validate_batches_processes(batches: list[list[dict[str, str]]], workers: int = 4) -> list[BatchValidationResult]:
    """Waliduje paczki równolegle z użyciem wielu procesów (omija GIL)."""
    with ProcessPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(validate_batch_worker, batches))