from inventree_universal_importer.core.search import Engine
from inventree_universal_importer.core.models import Query
from inventree_universal_importer.providers import ProviderConfig, REGISTRY
from inventree_universal_importer.core.http import ProviderError


class Cache:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, timeout=None):
        self.values[key] = value

    def add(self, key, value, timeout=None):
        if key in self.values:
            return False
        self.set(key, value)
        return True


def test_cache_and_rate_limit(monkeypatch):
    cache = Cache()
    configs = {"demo": ProviderConfig(enabled=True, cache_seconds=60)}
    engine = Engine(configs, cache)
    a, errors = engine.search(Query(text="sensor"))
    assert len(a) == 1 and not errors
    b, errors = engine.search(Query(text="sensor"))
    assert b[0].name == a[0].name and not errors
    c, errors = engine.search(Query(text="different"))
    assert errors[0]["code"] == "local_rate_limit"


def test_partial_results(monkeypatch):
    def fail(self, q):
        raise ProviderError("timeout")

    monkeypatch.setattr(REGISTRY["openfoodfacts"], "search", fail)
    products, errors = Engine(
        {slug: ProviderConfig(enabled=True) for slug in ("openfoodfacts", "demo")},
        Cache(),
    ).search(Query(text="sensor"))
    assert len(products) == 1 and errors == [
        {"provider": "openfoodfacts", "code": "timeout", "retry_after": 0}
    ]


def test_bad_provider_data_isolated(monkeypatch):
    def fail(self, q):
        raise KeyError("key-secret-data")

    monkeypatch.setattr(REGISTRY["openfoodfacts"], "search", fail)
    products, errors = Engine(
        {"openfoodfacts": ProviderConfig(enabled=True)}, Cache()
    ).search(Query(text="x"))
    assert not products and errors[0]["code"] == "invalid_provider_data"
