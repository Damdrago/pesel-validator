import argparse
from pathlib import Path

from core.generator import person_stream_with_errors
from core.iterator import BatchIterator
from core.validator import validate_batches_processes
from io_workers.exporter import export_results_concurrently
from utils.decorators import measure_time
from utils.logger import get_logger

logger = get_logger()


@measure_time
def run_pipeline(records: int, batch_size: int, error_rate: float, workers: int, output_dir: Path) -> None:
    """Uruchamia pełny potok: generowanie strumienia -> paczkowanie -> procesy -> eksport wątkami."""
    logger.info(
        "Start potoku: rekordy=%d, paczka=%d, odsetek_błędów=%.2f, procesy/wątki=%d",
        records,
        batch_size,
        error_rate,
        workers,
    )
    stream = person_stream_with_errors(limit=records, error_rate=error_rate)
    batches = list(BatchIterator(stream, batch_size=batch_size))
    logger.info("Utworzono %d paczek danych do przetworzenia.", len(batches))

    validation_results = validate_batches_processes(batches, workers=workers)
    export_results_concurrently(validation_results, output_dir=output_dir, max_threads=workers)


def parse_args() -> argparse.Namespace:
    """Parsuje argumenty wiersza poleceń (CLI)."""
    parser = argparse.ArgumentParser(
        description="Strumieniowy generator i równoległy walidator danych osobowych (PESEL, e-mail, telefon, kod pocztowy)."
    )
    parser.add_argument("-n", "--records", type=int, default=100_000, help="Liczba rekordów do wygenerowania (domyślnie: 100000)")
    parser.add_argument("-b", "--batch-size", type=int, default=10_000, help="Rozmiar pojedynczej paczki (domyślnie: 10000)")
    parser.add_argument("-e", "--error-rate", type=float, default=0.12, help="Odsetek celowo uszkodzonych rekordów 0.0–1.0 (domyślnie: 0.12)")
    parser.add_argument("-w", "--workers", type=int, default=4, help="Liczba procesów i wątków roboczych (domyślnie: 4)")
    parser.add_argument("-o", "--output", type=Path, default=Path("output"), help="Katalog wyjściowy dla plików CSV")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not (0.0 <= args.error_rate <= 1.0):
        raise ValueError("Parametr --error-rate musi zawierać się w przedziale [0.0, 1.0].")
    run_pipeline(
        records=args.records,
        batch_size=args.batch_size,
        error_rate=args.error_rate,
        workers=args.workers,
        output_dir=args.output,
    )


if __name__ == "__main__":
    main()