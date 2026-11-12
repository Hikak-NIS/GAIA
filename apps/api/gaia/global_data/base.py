from datetime import date
from typing import Protocol
from ..global_schemas import Area


class ProviderUnavailable(Exception):
    pass


class EnvironmentalProvider(Protocol):
    key: str

    def describe(self) -> dict: ...
    def fetch(self, area: Area, scenario: str, as_of: date) -> dict: ...


class PlannedProvider:
    key = ""
    name = ""
    url = ""
    requirements = ""
    products: tuple[str, ...] = ()

    def describe(self):
        return {
            "id": self.key,
            "name": self.name,
            "status": "not_connected",
            "available": False,
            "url": self.url,
            "requirements": self.requirements,
            "products": list(self.products),
        }

    def fetch(self, area: Area, scenario: str, as_of: date):
        raise ProviderUnavailable(f"{self.name}: источник не подключён. {self.requirements}")
