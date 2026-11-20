import csv
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from core.validator import BatchValidationResult
from utils.logger import get_logger

logger = get_logger()

VALID_FIELDNAMES = ("first_name", "last_name", "pesel", "gender", "email", "phone", "postal_code", "record_hash")
INVALID_FIELDNAMES = ("first_name", "last_name", "pesel", "email", "phone", "postal_code", "errors")


class ThreadSafeExportStats:
    """Współdzielony licznik wyeksportowanych rekordów synchronizowany blokadą threading.Lock."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total_valid = 0
        self.total_invalid = 0
        self.files_written = 0

    def update(self, valid_count: int, invalid_count: int, files_count: int) -> None:
        with self._lock:
            self.total_valid += valid_count
            self.total_invalid += invalid_count
            self.files_written += files_count


def _write_csv(file_path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    """Zapisuje listę słowników do pliku CSV."""
    with file_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_results_concurrently(
    results: list[BatchValidationResult],
    output_dir: Path,
    max_threads: int = 4,
) -> ThreadSafeExportStats:
    """
    Zapisuje zwalidowane paczki do osobnych plików CSV z użyciem kolejki (Queue),
    puli wątków (ThreadPoolExecutor) oraz blokady (Lock).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    task_queue: queue.Queue[tuple[int, BatchValidationResult]] = queue.Queue()
    stats = ThreadSafeExportStats()

    for idx, res in enumerate(results, start=1):
        task_queue.put((idx, res))

    def _worker() -> None:
        while True:
            try:
                part_idx, batch_res = task_queue.get_nowait()
            except queue.Empty:
                break

            try:
                written = 0
                if batch_res.valid_rows:
                    valid_file = output_dir / f"valid_part_{part_idx:03d}.csv"
                    _write_csv(valid_file, VALID_FIELDNAMES, batch_res.valid_rows)
                    written += 1

                if batch_res.invalid_rows:
                    invalid_file = output_dir / f"invalid_part_{part_idx:03d}.csv"
                    _write_csv(invalid_file, INVALID_FIELDNAMES, batch_res.invalid_rows)
                    written += 1

                stats.update(
                    valid_count=len(batch_res.valid_rows),
                    invalid_count=len(batch_res.invalid_rows),
                    files_count=written,
                )
            finally:
                task_queue.task_done()

    with ThreadPoolExecutor(max_workers=max_threads) as pool:
        futures = [pool.submit(_worker) for _ in range(max_threads)]
        for future in futures:
            future.result()

    logger.info(
        "Zapisano %d plików CSV (poprawne: %d, odrzucone: %d).",
        stats.files_written,
        stats.total_valid,
        stats.total_invalid,
    )
    return stats