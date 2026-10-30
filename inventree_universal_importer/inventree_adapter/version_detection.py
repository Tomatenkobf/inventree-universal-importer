from packaging.version import Version, InvalidVersion

# Update only after the integration gate has passed on the exact tag.
TESTED_VERSIONS = {"1.5.6", "1.5.7", "1.6.3"}


def status(version=None):
    if version is None:
        from InvenTree.version import INVENTREE_SW_VERSION

        version = INVENTREE_SW_VERSION
    try:
        parsed = Version(version)
        compatible = (
            str(parsed) in {"1.5.6", "1.5.7", "1.6.3"} and not parsed.is_prerelease
        )
    except InvalidVersion:
        compatible = False
    return {
        "version": version,
        "allowed": compatible,
        "tested": version in TESTED_VERSIONS,
        "warning": ""
        if version in TESTED_VERSIONS
        else "No automated backend compatibility result is recorded for this InvenTree version. See COMPATIBILITY.md.",
    }


def require_version():
    if not status()["allowed"]:
        raise ValueError(
            "Unsupported InvenTree version; import disabled. See COMPATIBILITY.md"
        )
