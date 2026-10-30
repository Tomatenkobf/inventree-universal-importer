from copy import deepcopy
from .normalization import identity


def equivalent(a, b):
    # Unknown variant/pack size is not evidence that it matches a known one.
    for key in ("variants", "packaging", "quantity"):
        if getattr(a, key) != getattr(b, key):
            return False
    if a.gtins and b.gtins:
        if not set(a.gtins) & set(b.gtins):
            return False
        if a.mpn and b.mpn and identity(a.mpn) != identity(b.mpn):
            return False
        return True
    return bool(
        a.manufacturer
        and b.manufacturer
        and a.mpn
        and b.mpn
        and identity(a.manufacturer) == identity(b.manufacturer)
        and identity(a.mpn) == identity(b.mpn)
    )


def score(product, query):
    if query.gtin and query.gtin in product.gtins:
        return 0.99, ["Exact validated GTIN; verify packaging in preview"]
    if query.mpn and identity(query.mpn) == identity(product.mpn):
        if query.manufacturer and identity(query.manufacturer) == identity(
            product.manufacturer
        ):
            return 0.97, ["Exact manufacturer and MPN"]
        return 0.70, ["Exact MPN; manufacturer identity not confirmed"]
    return 0.30, ["Discovery result; manual identity review required"]


def merge(products, query):
    groups = []
    for original in products:
        p = deepcopy(original)
        p.confidence, p.explanation = score(p, query)
        group = next((g for g in groups if equivalent(g, p)), None)
        if group is None:
            p.records = [original.export()]
            groups.append(p)
            continue
        group.records.append(original.export())
        for key in ("name", "description", "manufacturer", "mpn", "category"):
            incoming = getattr(p, key)
            old = getattr(group, key)
            if incoming and not old:
                setattr(group, key, incoming)
            elif incoming and old != incoming:
                group.conflicts.setdefault(key, [old])
                if incoming not in group.conflicts[key]:
                    group.conflicts[key].append(incoming)
        for key in ("image_urls", "datasheet_urls", "gtins"):
            setattr(
                group, key, list(dict.fromkeys(getattr(group, key) + getattr(p, key)))
            )
        for key, val in p.specifications.items():
            if key in group.specifications and group.specifications[key] != val:
                group.conflicts.setdefault(
                    "specifications." + key, [group.specifications[key]]
                ).append(val)
            else:
                group.specifications[key] = val
        for key, refs in p.provenance.items():
            group.provenance.setdefault(key, []).extend(refs)
        group.image_licenses.update(p.image_licenses)
        group.confidence = max(group.confidence, p.confidence)
    return sorted(groups, key=lambda p: p.confidence, reverse=True)
