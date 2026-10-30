import csv
import io
from .models import Query

ALIASES = {
    "ean": "gtin",
    "upc": "gtin",
    "barcode": "gtin",
    "gtin": "gtin",
    "mpn": "mpn",
    "manufacturer": "manufacturer",
    "brand": "manufacturer",
    "product name": "text",
    "name": "text",
    "ipn": "ipn",
}


def parse_csv(text, mapping=None):
    if not isinstance(text, str) or len(text.encode("utf-8")) > 1_000_000:
        raise ValueError("CSV is limited to 1 MB")
    stream = io.StringIO(text.lstrip("\ufeff"))
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(stream, dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("CSV requires a header row")
    names = [x.strip().lower() for x in reader.fieldnames]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate CSV headers")
    mapping = mapping or {
        x: ALIASES.get(x.strip().lower(), x.strip().lower()) for x in reader.fieldnames
    }
    out = []
    for number, row in enumerate(reader, 2):
        if len(out) >= 200:
            raise ValueError(
                "Maximum 200 rows; split larger files into reviewed batches"
            )
        mapped = {mapping.get(k, k): v or "" for k, v in row.items() if k is not None}
        item = {
            "row": number,
            "original": row,
            "quantity": mapped.get("quantity", ""),
            "location": mapped.get("location", ""),
            "category": mapped.get("category", ""),
        }
        try:
            item["query"] = Query.parse(mapped).__dict__
        except ValueError as exc:
            item["error"] = str(exc)
        out.append(item)
    return out


def report_csv(rows):
    target = io.StringIO()
    writer = csv.DictWriter(target, fieldnames=["row", "status", "part_id", "error"])
    writer.writeheader()
    for row in rows:
        safe = {k: str(row.get(k, "")) for k in writer.fieldnames}
        for k, v in safe.items():
            if v.startswith(("=", "+", "-", "@", "\t", "\r")):
                safe[k] = "'" + v
        writer.writerow(safe)
    return target.getvalue()
