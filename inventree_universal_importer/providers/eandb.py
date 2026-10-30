from .base import Provider, register
from ..core.normalization import barcode_for_api
from ..core.http import ProviderError


@register
class EANDB(Provider):
    slug = "eandb"
    modes = {"gtin"}

    def search(self, q):
        if not self.config.key:
            raise ProviderError("missing_credentials")
        raw = self.http.json(
            "GET",
            "https://ean-db.com/api/v2/product/" + barcode_for_api(q.gtin),
            headers={"Authorization": "Bearer " + self.config.key},
        )
        r = raw.get("product")
        if not r:
            return []

        def localized(values):
            return (
                values.get(self.config.language)
                or values.get("en")
                or next(iter(values.values()), "")
            )

        return [
            self.product(
                name=localized(r.get("titles", {})),
                manufacturer=localized((r.get("manufacturer") or {}).get("titles", {})),
                gtins=[r.get("barcode", "")],
                image_urls=[i.get("url", "") for i in r.get("images", [])],
                category=", ".join(
                    localized(c.get("titles", {})) for c in r.get("categories", [])
                ),
                source_product_id=r.get("barcode", ""),
                source_url="https://ean-db.com",
                metadata={"provider_data": r},
            )
        ]
