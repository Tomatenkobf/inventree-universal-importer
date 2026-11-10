# InvenTree Universal Product Importer

**0.1.0rc4 — staging release candidate.** One installable plugin for mixed inventory:
GTIN/UPC/EAN, manufacturer + MPN, manufacturer discovery, product text, IPN lookup,
and reviewed CSV imports. No separate application server, database or Redis service.

This is executable source, with prebuilt frontend assets, Python distributions,
unit tests and actual InvenTree database integration tests. It is **not a production
certification**: live provider access, commercial account entitlements and the full
browser workflow on your deployment still need the smoke test below.

## What is implemented

- A native plugin panel and dashboard widget on InvenTree 1.5.6 / 1.5.7.
- An additional native navigation page on 1.6.3 and 1.7.0 at
  `/web/plugin/universal-importer/import` (adjust the prefix if hosted below a subpath).
- Typed TypeScript UI using InvenTree's supported two-argument DOM renderer, the
  host's authenticated API client and Mantine theme variables. No second React
  runtime or separately deployed frontend.
- Open Food Facts, Icecat Product JSON, UPCitemdb, EAN-DB and Nexar adapters;
  each can be configured independently. A deterministic demo provider works offline.
- GTIN check digits, canonical 14-digit comparisons, conservative manufacturer/MPN
  matching, packaging/variant separation, explicit conflicts and field provenance.
- Existing-part checks by stored GTIN, configured identifier parameters, IPN and
  manufacturer-part relationships. Name-only records produce a potential-duplicate
  warning for an exact existing name; they are never automatically merged.
- Editable previews, selected fields, field comparisons, signed user-bound
  confirmation snapshots and permission checks. Nonempty values require explicit
  overwrite approval. Stale previews and changed duplicate sets are rejected.
- Transactional part/manufacturer/parameter/link creation, explicit enrichment,
  existing-category mapping, image/PDF downloads with domain allowlists and DNS
  pinning. No stock items or quantities are created.
- CSV validation, manual column mapping, per-row search/retry/skip, reviewed batch
  execution on InvenTree's existing worker, owner-scoped reports and CSV export.
- Django result caching where configured, database-backed cross-process request
  spacing, partial provider failures and bounded response/download sizes.

## Start here

1. Read [COMPATIBILITY.md](COMPATIBILITY.md) and back up a staging instance.
2. Install the supplied wheel using [docs/installation.md](docs/installation.md).
3. Activate App, URL and User Interface plugin support and this plugin; migrate
   its two plugin-owned tables, collect static assets and restart web + worker.
4. In plugin settings, enable `DEMO_ENABLED`, temporarily disable
   `OPENFOODFACTS_ENABLED`, and enter `4006381333931` or MPN `SENSOR-01` with
   manufacturer `Example Instruments`.
5. Open a part/category's **Universal Product Importer** panel, or add the widget
   to your dashboard. On 1.6.3 and 1.7.0, the navigation item opens the dedicated page.
6. Review, edit and import into staging. Enable manufacturer creation only if
   appropriate, or leave the manufacturer field unselected.
7. Disable the demo provider, configure real sources and run the live smoke test
   in [docs/testing.md](docs/testing.md).

## Release limits

- 1.5.6 has no custom UI route hook. Its supported panel/widget is the entry point;
  a separate native route is provided for 1.6.3 and 1.7.0. No core files are patched.
- GS1 has **no live adapter** without a specific authorized member-organisation API
  contract. The package does not guess a global GS1 endpoint.
- Commercial adapters are tested with mocks, not real accounts. No credentials
  were supplied. The attempted live Open Food Facts / UPCitemdb calls from the
  build environment did not succeed; live network operation is unverified.
- CSV files are limited to 1 MB / 200 rows; a background job accepts at most
  50 already-reviewed snapshots. Lookups are reviewed per row, not an unattended
  large-catalog crawl. Split larger files.
- Camera scanning uses browser `BarcodeDetector` where available. USB keyboard
  scanners and manual input are supported independently of camera availability.
- Categories and parameter templates must already exist. The plugin never creates
  arbitrary categories, supplier records or stock items. Existing images are not
  replaced by this release.
- Native shell rendering, camera hardware, live workers, PostgreSQL/MySQL concurrency
  and production load require deployment validation. The local database tests use
  SQLite; frontend tests use a DOM test environment.

## Development

```sh
python -m pip install '.[test]'
python -m pytest -q
cd frontend
npm ci
npm run build
npm test
cd ..
python -m build
```

For actual InvenTree integration, first install that exact tag's backend
requirements in a separate virtualenv, install this plugin into it, then run:

```sh
python tools/integration_check.py --inventree-root /absolute/path/to/InvenTree
```

The runner creates an isolated SQLite configuration and media directory. It does
not use your production configuration. See [docs/testing.md](docs/testing.md).

- [Configuration](docs/configuration.md)
- [Provider contracts and licensing](docs/providers.md)
- [Security and architecture](docs/architecture.md)
- [Upgrade and rollback](docs/upgrade.md)
- [Troubleshooting](docs/troubleshooting.md)
- [German quick start](docs/DE-SCHNELLSTART.md)

License: MIT for this plugin's code. External product data and media retain their
own licenses and account restrictions.
