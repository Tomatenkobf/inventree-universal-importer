from .base import Provider, register
from ..core.normalization import identity


@register
class Demo(Provider):
    slug = "demo"
    modes = {"gtin", "mpn", "text"}

    def search(self, q):
        p = self.product(
            name="Demo workshop sensor",
            description="Synthetic test record. No stock will be created.",
            manufacturer="Example Instruments",
            mpn="SENSOR-01",
            gtins=["4006381333931"],
            specifications={"Supply voltage": "5 V"},
            source_product_id="sensor-01",
            metadata={"synthetic": True},
        )
        if q.gtin and q.gtin not in p.gtins:
            return []
        if q.mpn and identity(q.mpn) != identity(p.mpn):
            return []
        return [p]
