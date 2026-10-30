"""Provider-independent, JSON-safe product contracts."""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


@dataclass(frozen=True)
class Query:
    gtin: str = ""
    manufacturer: str = ""
    mpn: str = ""
    text: str = ""
    ipn: str = ""

    @classmethod
    def parse(cls, value):
        from .normalization import gtin

        if not isinstance(value, dict):
            raise ValueError("Search must be an object")
        data = {}
        for key in cls.__dataclass_fields__:
            val = value.get(key, "")
            if not isinstance(val, str) or len(val) > 250:
                raise ValueError(f"Invalid {key}")
            data[key] = val.strip()
        if data["gtin"]:
            data["gtin"] = gtin(data["gtin"])
        if not any(data.values()):
            raise ValueError("Enter a barcode, MPN, manufacturer, IPN or search text")
        return cls(**data)


@dataclass
class Product:
    name: str = ""
    description: str = ""
    manufacturer: str = ""
    mpn: str = ""
    gtins: list[str] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    datasheet_urls: list[str] = field(default_factory=list)
    category: str = ""
    specifications: dict[str, str] = field(default_factory=dict)
    source: str = ""
    source_product_id: str = ""
    source_url: str = ""
    provenance: dict = field(default_factory=dict)
    image_licenses: dict = field(default_factory=dict)
    variants: dict = field(default_factory=dict)
    packaging: str = ""
    quantity: str = ""
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    confidence: float = 0.0
    explanation: list[str] = field(default_factory=list)
    conflicts: dict = field(default_factory=dict)
    records: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def export(self):
        return asdict(self)

    def finish(self):
        from .normalization import gtin, clean, safe_link

        self.name = clean(self.name, 250)
        self.description = clean(self.description, 10000)
        self.manufacturer = clean(self.manufacturer, 250)
        self.mpn = clean(self.mpn, 250)
        valid = []
        for value in self.gtins:
            try:
                valid.append(gtin(value))
            except (ValueError, TypeError):
                continue
        self.gtins = sorted(set(valid))
        for key in ("image_urls", "datasheet_urls"):
            setattr(
                self,
                key,
                list(dict.fromkeys(u for u in getattr(self, key) if safe_link(u)))[:20],
            )
        self.specifications = {
            clean(k, 100): clean(v, 500)
            for k, v in list(self.specifications.items())[:100]
            if k and v is not None
        }
        for key, value in self.export().items():
            if value and key not in ("provenance", "records", "metadata", "conflicts"):
                self.provenance.setdefault(
                    key,
                    [{"source": self.source, "url": self.source_url, "value": value}],
                )
        return self
