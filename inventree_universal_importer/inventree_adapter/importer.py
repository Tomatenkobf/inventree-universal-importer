import json
import uuid
import time
from dataclasses import fields
from django.core import signing
from django.db import transaction
from django.core.exceptions import PermissionDenied
from part.models import Part
from plugin.models import PluginConfig
from ..core.models import Product
from ..core.normalization import gtin
from . import parts, manufacturers, parameters, attachments
from .version_detection import require_version

SALT = "universal-importer.preview.v1"
FIELDS = {
    "name",
    "description",
    "ipn",
    "category",
    "manufacturer",
    "gtins",
    "specifications",
}


def parse_product(data):
    if not isinstance(data, dict) or len(json.dumps(data)) > 200_000:
        raise ValueError("Invalid or excessive product data")
    p = Product(
        **{
            key: value
            for key, value in data.items()
            if key in {f.name for f in fields(Product)}
        }
    )
    for key in ("name", "description", "manufacturer", "mpn", "category", "source"):
        if not isinstance(getattr(p, key), str):
            raise ValueError("Invalid " + key)
    if not isinstance(p.gtins, list) or len(p.gtins) > 20:
        raise ValueError("Invalid GTIN list")
    p.gtins = [gtin(g) for g in p.gtins]
    if not isinstance(p.specifications, dict) or len(p.specifications) > 100:
        raise ValueError("Invalid specifications")
    for key in ("image_urls", "datasheet_urls"):
        value = getattr(p, key)
        if (
            not isinstance(value, list)
            or len(value) > 20
            or any(not isinstance(v, str) for v in value)
        ):
            raise ValueError("Invalid " + key)
    for key in ("provenance", "image_licenses", "variants", "conflicts", "metadata"):
        if not isinstance(getattr(p, key), dict):
            raise ValueError("Invalid " + key)
    if not isinstance(p.records, list):
        raise ValueError("Invalid source records")
    return p.finish()


def preview(user, plugin, data):
    require_version()
    parts.require(user, "part.view_part")
    product = parse_product(data.get("product"))
    options = data.get("options") or {}
    if not isinstance(options, dict):
        raise ValueError("Invalid options")
    selected = options.get("fields", ["name", "description", "gtins"])
    if (
        not isinstance(selected, list)
        or any(not isinstance(v, str) for v in selected)
        or not set(selected) <= FIELDS
    ):
        raise ValueError("Invalid field selection")
    for key in ("overwrite", "specifications"):
        value = options.get(key, [])
        if (
            not isinstance(value, list)
            or len(value) > 100
            or any(not isinstance(v, str) for v in value)
        ):
            raise ValueError("Invalid " + key)
    for key in ("download_pdf", "media_rights_confirmed"):
        if key in options and not isinstance(options[key], bool):
            raise ValueError("Invalid " + key)
    for key in ("image_url", "datasheet_url"):
        if key in options and (
            not isinstance(options[key], str) or len(options[key]) > 2000
        ):
            raise ValueError("Invalid " + key)
    if len(product.name) > 100 or len(product.description) > 250:
        raise ValueError(
            "Edit preview: part name limit is 100, description limit is 250 characters"
        )
    ipn = options.get("ipn", "")
    if not isinstance(ipn, str) or len(ipn) > 100:
        raise ValueError("IPN limit is 100 characters")
    target_id = options.get("target_id")
    part = Part.objects.get(pk=int(target_id)) if target_id else None
    if part:
        if not plugin.get_setting("ALLOW_ENRICHMENT"):
            raise ValueError("Enrichment is disabled")
        parts.require(user, "part.change_part")
    else:
        parts.require(user, "part.add_part")
        if "name" not in selected or not product.name:
            raise ValueError("A new part requires a selected name")
    category = parts.category_id(product, options, plugin)
    options = {**options, "fields": selected, "category_id": category}
    existing = parts.duplicates(product, ipn, plugin)
    changes = []
    old = parts.snapshot(part)
    values = {
        "name": product.name,
        "description": product.description,
        "ipn": ipn,
        "category": category,
    }
    for key in selected:
        if key in values:
            before = (
                old.get("category_id" if key == "category" else key) if old else None
            )
            changes.append({"field": key, "before": before, "after": values[key]})
    if "manufacturer" in selected:
        changes.append(
            {
                "field": "manufacturer + MPN",
                "before": old["manufacturers"] if old else [],
                "after": {"manufacturer": product.manufacturer, "mpn": product.mpn},
            }
        )
    if "gtins" in selected:
        changes.append(
            {
                "field": "gtins",
                "before": ((old or {}).get("metadata") or {})
                .get(parts.NAMESPACE, {})
                .get("gtins", []),
                "after": product.gtins,
            }
        )
    if "specifications" in selected:
        mapping = json.loads(plugin.get_setting("PARAMETER_MAP") or "{}")
        current = {
            x["template_id"]: x["data"] for x in (old or {}).get("parameters", [])
        }
        for name in options.get("specifications", []):
            if name not in mapping or name not in product.specifications:
                raise ValueError(
                    "Select a specification with an existing template mapping: " + name
                )
            changes.append(
                {
                    "field": "specifications." + name,
                    "before": current.get(int(mapping[name])),
                    "after": product.specifications[name],
                }
            )
    for key in ("image_url", "datasheet_url"):
        if options.get(key):
            changes.append(
                {
                    "field": key,
                    "before": (old or {}).get(
                        "image" if key == "image_url" else "attachments"
                    ),
                    "after": options[key],
                }
            )
    payload = {
        "product": product.export(),
        "options": options,
        "user": user.pk,
        "fingerprint": parts.digest(part),
        "duplicates": [p["id"] for p in existing],
        "nonce": uuid.uuid4().hex,
    }
    return {
        "token": signing.dumps(payload, salt=SALT, compress=True),
        "changes": changes,
        "existing": existing,
        "current": old,
        "product": product.export(),
        "options": options,
    }


def commit(user, plugin, token, confirm=False, separate=False):
    require_version()
    if confirm is not True:
        raise ValueError("Explicit import confirmation required")
    if not isinstance(token, str) or len(token) > 400_000:
        raise ValueError("Invalid preview token")
    payload = signing.loads(token, salt=SALT, max_age=1800)
    if payload["user"] != user.pk:
        raise PermissionDenied("Preview belongs to a different user")
    product = parse_product(payload["product"])
    options = payload["options"]
    # Validate permission before network I/O.
    parts.require(
        user, "part.change_part" if options.get("target_id") else "part.add_part"
    )
    prepared = attachments.prepare(product, options, plugin)
    created_files = []
    try:
        with transaction.atomic():
            # Serialize all imports via the existing plugin configuration row.
            # SQLite rejects racing writes; caller receives a retryable conflict.
            lock = PluginConfig.objects.select_for_update().get(key=plugin.slug)
            receipts = (lock.metadata or {}).get("import_receipts", {})
            receipts = {
                k: v for k, v in receipts.items() if v["at"] > time.time() - 3600
            }
            if payload["nonce"] in receipts:
                return {
                    "part_id": receipts[payload["nonce"]]["part_id"],
                    "replayed": True,
                }
            part = (
                Part.objects.select_for_update().get(pk=options["target_id"])
                if options.get("target_id")
                else None
            )
            if part and not plugin.get_setting("ALLOW_ENRICHMENT"):
                raise ValueError("Enrichment is disabled")
            if parts.digest(part) != payload["fingerprint"]:
                raise ValueError("Part changed since preview; preview again")
            existing = parts.duplicates(product, options.get("ipn", ""), plugin)
            if [p["id"] for p in existing] != payload["duplicates"]:
                raise ValueError("Duplicate set changed; preview again")
            if existing and not part and separate is not True:
                raise ValueError(
                    "Duplicate exists; explicit separate-part confirmation required"
                )
            selected = set(options["fields"])
            overwrite = set(options.get("overwrite", []))
            if not part:
                part = Part(name=product.name)
            values = {
                "name": product.name,
                "description": product.description,
                "IPN": options.get("ipn", ""),
                "category_id": options.get("category_id"),
            }
            for key, field in [
                ("name", "name"),
                ("description", "description"),
                ("ipn", "IPN"),
                ("category", "category_id"),
            ]:
                if key not in selected:
                    continue
                old = getattr(part, field)
                new = values[field]
                if (
                    part.pk
                    and old not in (None, "")
                    and old != new
                    and key not in overwrite
                ):
                    raise ValueError(
                        "Nonempty field requires explicit overwrite approval: " + key
                    )
                setattr(part, field, new)
            part.full_clean()
            part.save()
            if "manufacturer" in selected:
                manufacturers.apply(part, product, user, plugin)
            if "specifications" in selected:
                parameters.apply(
                    part,
                    product,
                    user,
                    plugin,
                    options.get("specifications", []),
                    overwrite,
                )
            meta = dict(part.metadata or {})
            provenance = dict(meta.get(parts.NAMESPACE, {}))
            if "gtins" in selected:
                provenance["gtins"] = sorted(
                    set(provenance.get("gtins", []) + product.gtins)
                )
                parameters.gtin_parameter(part, product, user, plugin)
            history = provenance.get("history", [])
            history.append(
                {
                    "product": product.export(),
                    "selected_fields": sorted(selected),
                    "user_id": user.pk,
                }
            )
            provenance["history"] = history[-20:]
            meta[parts.NAMESPACE] = provenance
            part.metadata = meta
            part.save()
            attachments.apply(part, product, options, user, prepared, created_files)
            receipts[payload["nonce"]] = {"part_id": part.pk, "at": time.time()}
            metadata = dict(lock.metadata or {})
            metadata["import_receipts"] = receipts
            lock.metadata = metadata
            lock.save(update_fields=["metadata"])
            return {"part_id": part.pk, "created": not bool(options.get("target_id"))}
    except Exception:
        for storage, name in created_files:
            try:
                storage.delete(name)
            except Exception:
                pass
        raise
