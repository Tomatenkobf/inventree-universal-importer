"""All InvenTree ORM access lives in this package; no raw SQL or schema changes."""

import hashlib
import json
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from part.models import Part, PartCategory
from company.models import ManufacturerPart
from common.models import Parameter, Attachment
from ..core.normalization import gtin, identity

NAMESPACE = "universal_importer"


def require(user, permission):
    if not user.is_authenticated or not user.has_perm(permission):
        raise PermissionDenied("Missing permission: " + permission)


def snapshot(part):
    if not part:
        return None
    return {
        "id": part.pk,
        "name": part.name,
        "description": part.description,
        "ipn": part.IPN or "",
        "category_id": part.category_id,
        "image": str(part.image or ""),
        "metadata": part.metadata or {},
        "manufacturers": list(
            ManufacturerPart.objects.filter(part=part)
            .order_by("pk")
            .values("manufacturer_id", "manufacturer__name", "MPN")
        ),
        "attachments": list(
            Attachment.objects.filter(model_type="part", model_id=part.pk)
            .order_by("pk")
            .values("link", "attachment")
        ),
        "parameters": list(
            Parameter.objects.filter(
                model_type=ContentType.objects.get_for_model(Part), model_id=part.pk
            )
            .order_by("pk")
            .values("template_id", "data")
        ),
    }


def digest(part):
    return hashlib.sha256(
        json.dumps(snapshot(part), sort_keys=True, default=str).encode()
    ).hexdigest()


def duplicates(product, ipn="", plugin=None):
    ids = set()
    # JSON contains is unsupported on SQLite. Filter scalar GTIN parameter values
    # and inspect only metadata-bearing records in a bounded iterator instead.
    if product.gtins:
        for part in (
            Part.objects.exclude(metadata={})
            .only("pk", "metadata")
            .iterator(chunk_size=500)
        ):
            stored = (part.metadata or {}).get(NAMESPACE, {})
            if set(stored.get("gtins", [])) & set(product.gtins):
                ids.add(part.pk)
        templates = []
        if plugin:
            templates = json.loads(plugin.get_setting("IDENTIFIER_TEMPLATES") or "[]")
            configured = int(plugin.get_setting("GTIN_TEMPLATE") or 0)
            if configured:
                templates.append(configured)
        if templates:
            params = Parameter.objects.filter(
                model_type=ContentType.objects.get_for_model(Part),
                template_id__in=templates,
            )
            for value in params.values("model_id", "data").iterator(chunk_size=500):
                for candidate in value["data"].split(","):
                    try:
                        if gtin(candidate.strip()) in product.gtins:
                            ids.add(value["model_id"])
                    except ValueError:
                        continue
    if product.manufacturer and product.mpn:
        # Case/whitespace normalization without stripping meaningful punctuation.
        for mp in ManufacturerPart.objects.select_related("manufacturer").filter(
            MPN__iexact=product.mpn.strip()
        ):
            if mp.manufacturer and identity(mp.manufacturer.name) == identity(
                product.manufacturer
            ):
                ids.add(mp.part_id)
    if ipn:
        ids.update(Part.objects.filter(IPN__iexact=ipn).values_list("pk", flat=True))
    if (
        not product.gtins
        and not (product.manufacturer and product.mpn)
        and product.name
    ):
        # A same-name match is only a warning requiring review, never an automatic merge.
        ids.update(
            Part.objects.filter(name__iexact=product.name).values_list("pk", flat=True)
        )
    return list(
        Part.objects.filter(pk__in=ids)
        .order_by("pk")
        .values("id", "name", "description", "IPN", "category_id")
    )


def category_id(product, options, plugin):
    value = options.get("category_id")
    if value is None:
        value = json.loads(plugin.get_setting("CATEGORY_MAP") or "{}").get(
            product.category
        ) or plugin.get_setting("DEFAULT_CATEGORY")
    if value:
        category = PartCategory.objects.get(pk=int(value))
        return category.pk
    return None
