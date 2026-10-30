from .base import Provider, register
from ..core.normalization import barcode_for_api


@register
class OpenFoodFacts(Provider):
    slug = "openfoodfacts"
    modes = {"gtin", "text"}

    def search(self, q):
        fields = "code,product_name,generic_name,brands,image_front_url,image_url,categories,packaging,quantity,nutriments,ingredients_text"
        if q.gtin:
            data = self.http.json(
                "GET",
                "https://world.openfoodfacts.org/api/v2/product/"
                + barcode_for_api(q.gtin),
                params={"fields": fields},
            )
            rows = [data["product"]] if data.get("status") == 1 else []
        else:
            data = self.http.json(
                "GET",
                "https://world.openfoodfacts.org/cgi/search.pl",
                params={
                    "search_terms": q.text or q.manufacturer,
                    "search_simple": 1,
                    "action": "process",
                    "json": 1,
                    "page_size": 20,
                    "fields": fields,
                },
            )
            rows = data.get("products", [])
        result = []
        for row in rows:
            image = row.get("image_front_url") or row.get("image_url")
            link = "https://world.openfoodfacts.org/product/" + str(row.get("code", ""))
            result.append(
                self.product(
                    name=row.get("product_name", ""),
                    description=row.get("generic_name")
                    or row.get("ingredients_text", ""),
                    manufacturer=row.get("brands", ""),
                    gtins=[str(row.get("code", ""))],
                    image_urls=[image] if image else [],
                    category=row.get("categories", ""),
                    packaging=row.get("packaging", ""),
                    quantity=row.get("quantity", ""),
                    specifications=row.get("nutriments", {}),
                    source_product_id=str(row.get("code", "")),
                    source_url=link,
                    image_licenses={
                        image: {
                            "license": "CC BY-SA 3.0",
                            "attribution": "Open Food Facts contributors",
                            "url": link,
                        }
                    }
                    if image
                    else {},
                    metadata={
                        "license": "ODbL / Database Contents License",
                        "provider_data": row,
                    },
                )
            )
        return result
