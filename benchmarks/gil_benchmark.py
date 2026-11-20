import shutil
import statistics
import time
from pathlib import Path

import matplotlib.pyplot as plt

from core.generator import person_stream_with_errors
from core.iterator import BatchIterator
from core.validator import (
    validate_batches_processes,
    validate_batches_sequential,
    validate_batches_threads,
)
from io_workers.exporter import export_results_concurrently
from utils.logger import get_logger

logger = get_logger()


def measure_best_of(func, *args, repeats: int = 3, **kwargs) -> tuple[float, object]:
    """Uruchamia funkcję 'repeats' razy i zwraca najkrótszy (najbardziej miarodajny) czas oraz wynik."""
    times: list[float] = []
    last_result = None
    for _ in range(repeats):
        start = time.perf_counter()
        last_result = func(*args, **kwargs)
        times.append(time.perf_counter() - start)
    return min(times), last_result


def generate_chart(cpu_results: dict[str, float], io_results: dict[str, float], output_path: Path) -> None:
    """Generuje wykres słupkowy porównujący wpływ GIL na zadania CPU-bound oraz I/O-bound."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    # Wykres 1: Zadanie CPU-bound (walidacja regex + PESEL + SHA-256)
    cpu_labels = list(cpu_results.keys())
    cpu_values = list(cpu_results.values())
    bars1 = axes[0].bar(cpu_labels, cpu_values, color=["#6c757d", "#e07a5f", "#2a9d8f"])
    axes[0].set_title("Zadanie CPU-bound (Walidacja + SHA-256)")
    axes[0].set_ylabel("Czas wykonania [s] (mniej = lepiej)")
    axes[0].bar_label(bars1, fmt="%.3f s", padding=3)
    axes[0].set_ylim(0, max(cpu_values) * 1.2)

    # Wykres 2: Zadanie I/O-bound (zapis wielu plików CSV)
    io_labels = list(io_results.keys())
    io_values = list(io_results.values())
    bars2 = axes[1].bar(io_labels, io_values, color=["#6c757d", "#3d5a80"])
    axes[1].set_title("Zadanie I/O-bound (Zapis plików CSV)")
    axes[1].set_ylabel("Czas wykonania [s] (mniej = lepiej)")
    axes[1].bar_label(bars2, fmt="%.3f s", padding=3)
    axes[1].set_ylim(0, max(io_values) * 1.2)

    plt.suptitle("Wpływ mechanizmu GIL w Pythonie na współbieżność i równoległość", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close(fig)


def run_benchmark(total_records: int = 250_000, batch_size: int = 12_500, workers: int = 4) -> None:
    """Przeprowadza kompletny benchmark GIL i wypisuje gotową tabelę Markdown do README."""
    logger.info("Przygotowanie %d rekordów w paczkach po %d...", total_records, batch_size)
    batches = list(BatchIterator(person_stream_with_errors(limit=total_records, error_rate=0.15), batch_size=batch_size))

    logger.info("1/3 Pomiar CPU-bound: sekwencyjnie...")
    t_seq, res_seq = measure_best_of(validate_batches_sequential, batches)

    logger.info("2/3 Pomiar CPU-bound: wątki (ThreadPoolExecutor, workers=%d)...", workers)
    t_thr, _ = measure_best_of(validate_batches_threads, batches, workers=workers)

    logger.info("3/3 Pomiar CPU-bound: procesy (ProcessPoolExecutor, workers=%d)...", workers)
    t_proc, _ = measure_best_of(validate_batches_processes, batches, workers=workers)

    bench_out = Path("output_bench")
    logger.info("Pomiar I/O-bound: zapis plików CSV (1 wątek vs %d wątków)...", workers)

    def _io_run(threads: int) -> None:
        if bench_out.exists():
            shutil.rmtree(bench_out)
        export_results_concurrently(res_seq, output_dir=bench_out, max_threads=threads)

    t_io_seq, _ = measure_best_of(_io_run, 1, repeats=2)
    t_io_thr, _ = measure_best_of(_io_run, workers, repeats=2)

    if bench_out.exists():
        shutil.rmtree(bench_out)

    chart_path = Path("benchmarks/gil_results.png")
    generate_chart(
        cpu_results={"Sekwencyjnie": t_seq, f"Wątki ({workers})": t_thr, f"Procesy ({workers})": t_proc},
        io_results={"Sekwencyjnie (1 wątek)": t_io_seq, f"Wątki ({workers})": t_io_thr},
        output_path=chart_path,
    )

    print("\n=== GOTOWA TABELA DO WKLEJENIA DO README.md ===\n")
    print("| Typ zadania | Tryb wykonania | Czas [s] | Przyspieszenie względem sekwencyjnego |")
    print("| :--- | :--- | :---: | :---: |")
    print(f"| CPU-bound (walidacja + SHA-256) | Sekwencyjnie (1 wątek) | {t_seq:.3f} s | 1.00x |")
    print(f"| CPU-bound (walidacja + SHA-256) | Wątki (`ThreadPoolExecutor`, {workers}) | {t_thr:.3f} s | {t_seq / t_thr:.2f}x |")
    print(f"| CPU-bound (walidacja + SHA-256) | Procesy (`ProcessPoolExecutor`, {workers}) | {t_proc:.3f} s | **{t_seq / t_proc:.2f}x** |")
    print(f"| I/O-bound (zapis 40 plików CSV) | Sekwencyjnie (1 wątek) | {t_io_seq:.3f} s | 1.00x |")
    print(f"| I/O-bound (zapis 40 plików CSV) | Wątki (`ThreadPoolExecutor`, {workers}) | {t_io_thr:.3f} s | **{t_io_seq / t_io_thr:.2f}x** |")
    print(f"\nWykres zapisano w: {chart_path}\n")


if __name__ == "__main__":
    run_benchmark()