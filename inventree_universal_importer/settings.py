from .providers import REGISTRY


def setting(name, default, kind=str, **extra):
    return dict(name=name, default=default, validator=kind, **extra)


SETTINGS = {
    "ENABLED": setting("Enable lookup and import", True, bool),
    "LANGUAGE": setting("Preferred language", "en"),
    "DEFAULT_CATEGORY": setting("Default existing category ID", 0, int),
    "CATEGORY_MAP": setting("Provider category to existing category ID (JSON)", "{}"),
    "SEARCH_TIMEOUT": setting("Total search budget in seconds", 30, int),
    "USER_AGENT": setting(
        "API user agent (add administrator contact)", "InvenTree-Universal-Importer/0.1"
    ),
    "ALLOW_MANUFACTURER_CREATE": setting("Allow manufacturer creation", False, bool),
    "ALLOW_ENRICHMENT": setting("Allow enrichment of existing parts", True, bool),
    "GTIN_TEMPLATE": setting(
        "Existing GTIN parameter template ID (0 uses metadata only)", 0, int
    ),
    "IDENTIFIER_TEMPLATES": setting(
        "Additional identifier parameter template IDs (JSON)", "[]"
    ),
    "PARAMETER_MAP": setting(
        "Specification name to existing parameter template ID (JSON)", "{}"
    ),
    "ALLOW_MEDIA": setting("Allow local image/PDF downloads", False, bool),
    "MEDIA_HOSTS": setting(
        "Exact allowed media hosts, comma-separated", "images.openfoodfacts.org"
    ),
}
for slug in REGISTRY:
    prefix = slug.upper() + "_"
    SETTINGS[prefix + "ENABLED"] = setting(
        slug + " enabled", slug == "openfoodfacts", bool
    )
    SETTINGS[prefix + "PRIORITY"] = setting(
        slug + " priority", list(REGISTRY).index(slug) * 10, int
    )
    SETTINGS[prefix + "TIMEOUT"] = setting(slug + " timeout seconds", 8, int)
    SETTINGS[prefix + "INTERVAL"] = setting(
        slug + " minimum seconds between requests", 6, int
    )
    SETTINGS[prefix + "CACHE_SECONDS"] = setting(
        slug + " cache seconds (only if license permits)",
        3600 if slug in ("openfoodfacts", "demo") else 0,
        int,
    )
    for key, label in [
        ("KEY", "API key / token / Nexar client ID"),
        ("USERNAME", "Icecat username"),
        ("SECRET", "Nexar client secret / Icecat content token"),
    ]:
        SETTINGS[prefix + key] = setting(
            slug + " " + label, "", protected=key != "USERNAME"
        )


def provider_configs(plugin):
    from .providers import ProviderConfig

    result = {}
    for slug in REGISTRY:
        values = {
            k: plugin.get_setting(slug.upper() + "_" + k.upper())
            for k in (
                "enabled",
                "priority",
                "timeout",
                "interval",
                "cache_seconds",
                "key",
                "username",
                "secret",
            )
        }
        values["language"] = plugin.get_setting("LANGUAGE")
        values["user_agent"] = plugin.get_setting("USER_AGENT")
        for k in ("priority", "timeout", "interval", "cache_seconds"):
            values[k] = int(values[k])
        result[slug] = ProviderConfig(**values)
    return result
