from collections.abc import Iterator
from typing import Generic, TypeVar

T = TypeVar("T")


class BatchIterator(Generic[T]):
    """Własny iterator implementujący protokół (__iter__, __next__) dzielący strumień na paczki."""

    def __init__(self, source: Iterator[T], batch_size: int = 10_000) -> None:
        if batch_size <= 0:
            raise ValueError("Rozmiar paczki (batch_size) musi być większy od zera.")
        self._source = iter(source)
        self._batch_size = batch_size

    def __iter__(self) -> "BatchIterator[T]":
        """Zwraca samego siebie zgodnie z protokołem iteratora."""
        return self

    def __next__(self) -> list[T]:
        """Pobiera ze strumienia kolejną paczkę o maksymalnym rozmiarze batch_size."""
        batch: list[T] = []
        for _ in range(self._batch_size):
            try:
                batch.append(next(self._source))
            except StopIteration:
                break

        if not batch:
            raise StopIteration
        return batch