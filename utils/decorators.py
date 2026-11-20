import functools
import time
from typing import Any, Callable, TypeVar

from utils.logger import get_logger

F = TypeVar("F", bound=Callable[..., Any])
logger = get_logger()


def measure_time(func: F) -> F:
    """Dekorator mierzący i logujący czas wykonania udekorowanej funkcji."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info("Funkcja '%s' wykonała się w %.4f s", func.__name__, elapsed)
        return result

    return wrapper  # type: ignore[return-value]


def validate_record_limit(min_records: int = 1, max_records: int = 5_000_000) -> Callable[[F], F]:
    """Dekorator z parametrami sprawdzający, czy argument 'limit' lub 'count' mieści się w zakresie."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            limit = kwargs.get("limit") if "limit" in kwargs else kwargs.get("count")
            if limit is None and len(args) >= 1 and isinstance(args[0], int):
                limit = args[0]

            if limit is not None and not (min_records <= limit <= max_records):
                raise ValueError(
                    f"Liczba rekordów ({limit}) musi zawierać się w przedziale [{min_records}, {max_records}]."
                )
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator