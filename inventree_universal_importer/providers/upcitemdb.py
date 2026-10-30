from .base import Provider, register
from ..core.normalization import barcode_for_api


@register
class UPCItemDB(Provider):
    slug = "upcitemdb"
    modes = {"gtin", "text"}

    def search(self, q):
        paid = bool(self.config.key)
        headers = {"user_key": self.config.key, "key_type": "3scale"} if paid else {}
        mode = "lookup" if q.gtin else "search"
        params = (
            {"upc": barcode_for_api(q.gtin)}
            if q.gtin
            else {"s": q.text or q.manufacturer}
        )
        raw = self.http.json(
            "GET",
            "https://api.upcitemdb.com/prod/"
            + ("v1" if paid else "trial")
            + "/"
            + mode,
            headers=headers,
            params=params,
        )
        return [
            self.product(
                name=r.get("title", ""),
                description=r.get("description", ""),
                manufacturer=r.get("brand", ""),
                mpn=r.get("model", ""),
                gtins=[r.get("ean", ""), r.get("upc", "")],
                image_urls=r.get("images", []),
                category=r.get("category", ""),
                variants={k: r[k] for k in ("size", "color") if r.get(k)},
                source_product_id=r.get("ean") or r.get("upc", ""),
                source_url="https://www.upcitemdb.com/upc/"
                + (r.get("upc") or r.get("ean", "")),
                metadata={"provider_data": r},
            )
            for r in raw.get("items", [])
        ]
