from dataclasses import dataclass
from ..core.models import Product


@dataclass
class ProviderConfig:
    enabled: bool = False
    priority: int = 50
    timeout: int = 8
    interval: int = 6
    cache_seconds: int = 0
    key: str = ""
    username: str = ""
    secret: str = ""
    language: str = "en"
    user_agent: str = "InvenTree-Universal-Importer/0.1"


class Provider:
    slug = ""
    modes = frozenset()

    def __init__(self, config, transport):
        self.config, self.http = config, transport

    def supports(self, q):
        return (
            ("gtin" in self.modes and bool(q.gtin))
            or ("mpn" in self.modes and bool(q.mpn))
            or ("text" in self.modes and bool(q.text or q.manufacturer))
        )

    def search(self, query):
        raise NotImplementedError("Provider subclasses must implement search")

    def product(self, **kwargs):
        return Product(source=self.slug, **kwargs).finish()


REGISTRY = {}


def register(cls):
    if not cls.slug or cls.slug in REGISTRY:
        raise ValueError("Provider slug must be unique")
    REGISTRY[cls.slug] = cls
    return cls
