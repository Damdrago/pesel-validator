import functools
from typing import Any, Callable, Self

from core.patterns import EMAIL_RE, PHONE_RE, POSTAL_RE, verify_pesel_checksum_and_date


def require_verified_state(method: Callable[..., Any]) -> Callable[..., Any]:
    """Własny dekorator metody korzystający z self — wymaga poprawnego stanu walidacji rekordu."""

    @functools.wraps(method)
    def wrapper(self: "PersonRecord", *args: Any, **kwargs: Any) -> Any:
        if not self.is_valid:
            raise PermissionError(
                f"Operacja '{method.__name__}' zablokowana: rekord dla {self.first_name} {self.last_name} zawiera błędy."
            )
        return method(self, *args, **kwargs)

    return wrapper


class PersonRecord:
    """Model danych osobowych z automatyczną walidacją pól i dekoratorami metod."""

    def __init__(
        self,
        first_name: str,
        last_name: str,
        pesel: str,
        email: str,
        phone: str,
        postal_code: str,
    ) -> None:
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phone = phone
        self.postal_code = postal_code
        self.gender: str | None = None
        self.validation_errors: list[str] = []
        self._pesel = ""
        # Wywołuje setter @pesel.setter, który automatycznie uruchamia walidację
        self.pesel = pesel

    @property
    def pesel(self) -> str:
        """Zwraca numer PESEL rekordu."""
        return self._pesel

    @pesel.setter
    def pesel(self, value: str) -> None:
        """Ustawia numer PESEL i automatycznie aktualizuje stan walidacji całego rekordu."""
        self._pesel = value.strip()
        self._revalidate()

    def _revalidate(self) -> None:
        """Sprawdza wszystkie pola rekordu pod kątem wzorców regex oraz sumy kontrolnej PESEL."""
        self.validation_errors.clear()
        pesel_ok, detected_gender = verify_pesel_checksum_and_date(self._pesel)
        if not pesel_ok:
            self.validation_errors.append("INVALID_PESEL")
        self.gender = detected_gender

        if not EMAIL_RE.match(self.email):
            self.validation_errors.append("INVALID_EMAIL")
        if not PHONE_RE.match(self.phone):
            self.validation_errors.append("INVALID_PHONE")
        if not POSTAL_RE.match(self.postal_code):
            self.validation_errors.append("INVALID_POSTAL_CODE")

    @property
    def is_valid(self) -> bool:
        """Zwraca True, jeśli rekord przeszedł pomyślnie wszystkie reguły walidacji."""
        return len(self.validation_errors) == 0

    @classmethod
    def from_dict(cls, raw_data: dict[str, str]) -> Self:
        """Metoda wytwórcza (@classmethod) tworząca obiekt PersonRecord ze słownika."""
        return cls(
            first_name=raw_data.get("first_name", ""),
            last_name=raw_data.get("last_name", ""),
            pesel=raw_data.get("pesel", ""),
            email=raw_data.get("email", ""),
            phone=raw_data.get("phone", ""),
            postal_code=raw_data.get("postal_code", ""),
        )

    @require_verified_state
    def to_export_row(self) -> dict[str, str]:
        """Zwraca słownik gotowy do eksportu CSV — chroniony dekoratorem @require_verified_state."""
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "pesel": self.pesel,
            "gender": self.gender or "",
            "email": self.email,
            "phone": self.phone,
            "postal_code": self.postal_code,
        }