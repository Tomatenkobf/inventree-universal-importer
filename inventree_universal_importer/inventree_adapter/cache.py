import time
from django.core.cache import cache


class SharedRateCache:
    """Django cache for permitted product data; DB atomic compare/update for quotas."""

    def get(self, key):
        return cache.get(key)

    def set(self, key, value, timeout=60):
        from ..models import RateGate

        if key.startswith(("upi:rate:", "upi:user:")):
            until = time.time() + max(1, timeout)
            RateGate.objects.get_or_create(key=key)
            RateGate.objects.filter(key=key, expires__lt=until).update(expires=until)
        else:
            cache.set(key, value, timeout=timeout)

    def add(self, key, value, timeout=60):
        from ..models import RateGate

        now = time.time()
        RateGate.objects.get_or_create(key=key)
        return bool(
            RateGate.objects.filter(key=key, expires__lte=now).update(
                expires=now + max(1, timeout)
            )
        )
