# Configuration

All runtime settings are in InvenTree's plugin administration. No keys belong in
source, CSV files, frontend code or CI configuration.

## General settings

| Key | Default | Behavior |
| --- | --- | --- |
| `ENABLED` | true | Stops plugin API work when false |
| `LANGUAGE` | en | Requested Icecat / EAN-DB language |
| `DEFAULT_CATEGORY` | 0 | Existing category ID; 0 leaves it unset |
| `CATEGORY_MAP` | `{}` | Provider category label → existing category ID |
| `SEARCH_TIMEOUT` | 30 | Budget checked between providers; active transport has its own bounds |
| `USER_AGENT` | plugin/version | Add your administrative contact for provider compliance |
| `ALLOW_MANUFACTURER_CREATE` | false | Also requires the user's company-create permission |
| `ALLOW_ENRICHMENT` | true | Updates require part-change permission and a fresh preview |
| `GTIN_TEMPLATE` | 0 | Existing part parameter template; 0 retains GTINs only in metadata |
| `IDENTIFIER_TEMPLATES` | `[]` | Additional existing GTIN/EAN/UPC parameter template IDs to search |
| `PARAMETER_MAP` | `{}` | Provider specification name → existing part parameter template ID |
| `ALLOW_MEDIA` | false | Enables user-selected local downloads |
| `MEDIA_HOSTS` | images.openfoodfacts.org | Exact allowed HTTPS hosts; no wildcard/subdomain inheritance |

Example values (replace the IDs with ones from your own installation):

```json
{"Sensors": 12, "Computers": 18}
```

```json
{"Supply voltage": 31, "Memory": 32}
```

```json
[42, 43]
```

A template's model type must be `part`. Categories/templates are selected or mapped,
never created from arbitrary provider strings. A GTIN parameter stores canonical
14-digit GTINs separated by commas. Original provider data remains in provenance.

## Provider settings

Each registered adapter receives `<PROVIDER>_ENABLED`, `_KEY`, `_USERNAME`, `_SECRET`,
`_PRIORITY`, `_TIMEOUT`, `_INTERVAL` and `_CACHE_SECONDS` settings.

- Lower priority numbers run first.
- Timeout is clamped to 1–20 seconds per HTTP request. Reads and JSON sizes are bounded.
- Interval is a shared minimum request spacing, in seconds; default 6. Set it to
  comply with your account's limits. Provider HTTP 429 responses extend the cooldown.
- Only Open Food Facts and demo results are cached by default (one hour). All other
  provider result caches default to zero until your account terms permit retention.
- Key/secret fields are `protected` InvenTree settings. Logs include only provider
  name, record count and a fixed error code. They do not include query strings,
  credentials, raw response bodies or exceptions.
- `_USERNAME` is used by Icecat. Nexar uses `_KEY` as client ID and `_SECRET` as
  client secret. EAN-DB uses `_KEY` as its bearer JWT. UPCitemdb uses `_KEY` for paid
  access; an empty key selects the documented trial API.

The UI always requires confirmation. Duplicate checking cannot be disabled.
The plugin never uses an EAN as IPN implicitly: select and enter IPN explicitly.
Manufacturer and MPN are a relationship, never a supplier SKU.

## Enrichment

Choose an existing match or enter a target part ID, then select the fields to
change. Nonempty fields are protected by default. For an intentional replacement,
enter its field name in the explicit overwrite list (`name`, `description`, `ipn`,
`category`, or `specifications.<parameter template name>`). Build a fresh comparison
and inspect both current and proposed values before confirming.

GTINs in metadata are accumulated. A conflicting existing GTIN parameter is not
silently overwritten: resolve it in InvenTree first. Existing manufacturer parts
are preserved; a selected new manufacturer + MPN is appended. This release never
replaces an existing part image.

## CSV and background work

Headers such as `EAN`, `UPC`, `GTIN`, `MPN`, `Manufacturer`, `Brand`, `Product name`,
`Name` and `IPN` are auto-mapped. Supply JSON mappings for other headers, for example
`{"Artikelnummer":"mpn","Hersteller":"manufacturer"}`. Values remain text, including
leading zeroes. Quantity/location are displayed only and never produce stock.

Search each valid row, review the selected product, build the final comparison,
check its approval box and either import immediately or add it to the reviewed
batch. **Queue reviewed imports** submits at most 50 approved snapshots to the
existing InvenTree worker. Snapshots expire after 30 minutes; submit promptly.
The job rechecks permissions and duplicates at execution, and reports per-row
failures. Refresh its report or download the CSV session report. Failed rows need
new previews. A worker interrupted mid-job can be recovered after ten minutes of
inactivity; completed rows are not executed again.

Job reports are owner-scoped; tokens are removed from completed rows. Old jobs are
purged on subsequent enqueue calls after 30 days. The current UI keeps the current
job ID and session report in memory; keep the downloaded report before leaving
the page. An administrator can inspect persisted job rows through Django tooling.
