import re
import unicodedata
from html import unescape
from urllib.parse import urlsplit


def gtin(value):
    if not isinstance(value, str):
        raise ValueError("GTIN must be text (leading zeroes are significant)")
    value = re.sub(r"[ -]", "", value.strip())
    if len(value) not in (8, 12, 13, 14) or not value.isascii() or not value.isdigit():
        raise ValueError("GTIN must contain 8, 12, 13 or 14 digits")
    total = sum(
        int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(value[:-1]))
    )
    if (10 - total % 10) % 10 != int(value[-1]):
        raise ValueError("Invalid GTIN check digit")
    return value.zfill(14)


def barcode_for_api(value):
    # Keep nonzero packaging indicators; GTIN-8 is retained at eight digits.
    return (
        value.lstrip("0").zfill(8)
        if len(value.lstrip("0")) <= 8
        else value.lstrip("0").zfill(12)
    )


def identity(value):
    return " ".join(unicodedata.normalize("NFKC", value or "").casefold().split())


def clean(value, limit=500):
    text = unescape(re.sub(r"<[^>]*>", " ", str(value or "")))
    return "".join(c for c in text if c.isprintable() or c in "\n\t").strip()[:limit]


def safe_link(value):
    try:
        u = urlsplit(value)
        return (
            u.scheme == "https"
            and bool(u.hostname)
            and not u.username
            and not u.password
            and u.port in (443, None)
        )
    except (ValueError, TypeError):
        return False
