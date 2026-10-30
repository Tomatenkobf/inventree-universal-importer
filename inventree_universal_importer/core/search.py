import hashlib
import json
import logging
import time
from dataclasses import asdict
from .http import Transport, ProviderError
from .models import Product
from .matching import merge
from ..providers import REGISTRY

logger = logging.getLogger(__name__)


class Engine:
    def __init__(self, configs, cache, timeout=30):
        self.configs, self.cache, self.timeout = (
            configs,
            cache,
            max(1, min(timeout, 60)),
        )

    def search(self, q):
        results = []
        errors = []
        deadline = time.monotonic() + self.timeout
        for slug, config in sorted(self.configs.items(), key=lambda x: x[1].priority):
            if not config.enabled:
                continue
            provider = REGISTRY[slug](
                config,
                Transport(
                    min(config.timeout, max(1, deadline - time.monotonic())),
                    config.user_agent,
                ),
            )
            if not provider.supports(q):
                continue
            if time.monotonic() > deadline:
                errors.append({"provider": slug, "code": "search_deadline"})
                continue
            fingerprint = hashlib.sha256(
                json.dumps(asdict(config), sort_keys=True).encode()
            ).hexdigest()
            key = (
                "upi:result:"
                + slug
                + ":"
                + hashlib.sha256(
                    (fingerprint + json.dumps(asdict(q), sort_keys=True)).encode()
                ).hexdigest()
            )
            try:
                cached = self.cache.get(key) if config.cache_seconds else None
                if cached is not None:
                    results.extend(Product(**p) for p in cached)
                    continue
                # Atomic cache.add; shared cache required for cross-worker API quotas.
                if not self.cache.add(
                    "upi:rate:" + slug, True, timeout=max(1, config.interval)
                ):
                    raise ProviderError("local_rate_limit", config.interval)
                found = provider.search(q)
                if config.cache_seconds:
                    self.cache.set(
                        key, [p.export() for p in found], timeout=config.cache_seconds
                    )
                results.extend(found)
                logger.info("Provider %s completed; records=%d", slug, len(found))
            except ProviderError as exc:
                if exc.retry_after:
                    self.cache.set("upi:rate:" + slug, True, timeout=exc.retry_after)
                errors.append(
                    {"provider": slug, "code": exc.code, "retry_after": exc.retry_after}
                )
                logger.warning("Provider %s failed: %s", slug, exc.code)
            except Exception:
                # Never expose response bodies, credential-bearing URLs or tracebacks.
                errors.append({"provider": slug, "code": "invalid_provider_data"})
                logger.warning("Provider %s failed: invalid_provider_data", slug)
        return merge(results, q), errors
