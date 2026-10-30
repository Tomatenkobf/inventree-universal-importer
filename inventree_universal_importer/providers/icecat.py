from .base import Provider, register
from ..core.normalization import barcode_for_api
from ..core.http import ProviderError


@register
class Icecat(Provider):
    slug = "icecat"
    modes = {"gtin", "mpn"}

    def supports(self, q):
        return bool(q.gtin or (q.mpn and q.manufacturer))

    def search(self, q):
        if not self.config.username and not self.config.key:
            raise ProviderError("missing_credentials")
        params = {"lang": self.config.language.upper()}
        if self.config.username:
            params["shopname"] = self.config.username
        if q.gtin:
            params["GTIN"] = barcode_for_api(q.gtin)
        else:
            params.update({"Brand": q.manufacturer, "ProductCode": q.mpn})
        headers = {}
        if self.config.key:
            headers["api-token"] = self.config.key
        if self.config.secret:
            headers["content-token"] = self.config.secret
        raw = self.http.json(
            "GET", "https://live.icecat.biz/api", params=params, headers=headers
        )
        row = raw.get("data") or {}
        if not row:
            if raw.get("error"):
                raise ProviderError("catalog_access_or_product_unavailable")
            return []
        info = row.get("GeneralInfo") or {}
        desc = info.get("Description") or {}
        specs = {}
        for group in row.get("FeaturesGroups", []):
            for feature in group.get("Features", []):
                name = (feature.get("Feature") or {}).get("Name", {})
                if isinstance(name, dict):
                    name = name.get("Value", "")
                if name:
                    specs[name] = feature.get("PresentationValue", "")
        images = [(row.get("Image") or {}).get("HighPic", "")]
        images += [g.get("Pic", "") for g in row.get("Gallery", [])]
        datasheets = [
            m.get("URL", "")
            for m in row.get("Multimedia", [])
            if m.get("ContentType") == "application/pdf"
            or str(m.get("URL", "")).lower().endswith(".pdf")
        ]
        brand = info.get("Brand", "")
        if isinstance(brand, dict):
            brand = brand.get("Name", "")
        category = (info.get("Category") or {}).get("Name", {})
        if isinstance(category, dict):
            category = category.get("Value", "")
        return [
            self.product(
                name=info.get("Title", ""),
                description=desc.get("LongDesc") or desc.get("ShortDesc", ""),
                manufacturer=brand,
                mpn=info.get("BrandPartCode", ""),
                gtins=info.get("GTIN", []),
                image_urls=images,
                datasheet_urls=datasheets,
                category=category,
                specifications=specs,
                source_product_id=str(info.get("IcecatId", "")),
                source_url="https://icecat.biz/p/"
                + str(info.get("IcecatId", ""))
                + ".html",
                image_licenses={
                    u: {
                        "license": "Icecat account/brand terms; verify redistribution rights"
                    }
                    for u in images
                    if u
                },
                metadata={"provider_data": row},
            )
        ]
