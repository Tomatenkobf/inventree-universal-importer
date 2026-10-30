# Provider contracts and data rights

The provider layer is independent of Django and InvenTree models. `Provider.search`
returns normalized `Product` objects. The engine queries enabled, capable adapters,
isolates failures and merges only records with strong shared identifiers and
compatible known variant/packaging data. Similar names alone never justify merging.

| Adapter | Implemented request modes | Credentials / restrictions |
| --- | --- | --- |
| Open Food Facts | GTIN lookup, text/manufacturer discovery | No key; user agent, quotas and attribution required |
| Icecat | GTIN or brand + product code | Own account username and/or API token; optional content token; content availability depends on account/brand |
| UPCitemdb | GTIN lookup, text discovery | Documented trial access or paid `user_key` |
| EAN-DB | Barcode lookup | Account bearer JWT |
| Nexar | Supply GraphQL text/MPN search, specs, best datasheet | OAuth client ID/secret and Supply entitlement |
| Demo | Synthetic lookup/search | No network; disabled by default |
| GS1 | Unavailable | A specific licensed API contract/documentation is needed |

Commercial response parsing and authentication flows are fixture-tested. These are
not proof of account entitlement or a successful live API call. The demo is a
synthetic sensor record, not a GS1 ownership verification service.

## Verified API references

Checked against official documentation and tagged source during implementation:

- Open Food Facts API: https://openfoodfacts.github.io/openfoodfacts-server/api/
  Product lookup uses `/api/v2/product/{barcode}`; discovery uses `/cgi/search.pl`.
- Icecat manual: https://iceclog.com/manual-for-icecat-json-product-requests/
  `https://live.icecat.biz/api`, `GTIN` or `Brand` + `ProductCode`; `shopname`,
  `api-token` and optionally `content-token`. Free catalog coverage is not universal.
- UPCitemdb: https://www.upcitemdb.com/wp/docs/main/development/getting-started/
  `https://api.upcitemdb.com/prod/{trial|v1}/{lookup|search}`.
- EAN-DB: https://ean-db.com/docs and https://ean-db.com/docs/productApi
  `https://ean-db.com/api/v2/product/{barcode}` with bearer authorization.
- Nexar: https://support.nexar.com/support/solutions/articles/101000434612-how-to-explore-the-data-model
  and https://nexar.freshdesk.com/support/solutions/articles/101000471994-authorization
  Identity token request at `https://identity.nexar.com/connect/token`; GraphQL at
  `https://api.nexar.com/graphql`. A typed `$q` variable avoids query interpolation.
- GS1: https://www.gs1.org/services/verified-by-gs1 — service access is not assumed
  to mean an unrestricted, public product/media API.

Nexar currently requests a token per uncached lookup; it does not persist OAuth
access tokens. Lifecycle information is retained when present in provider data but
is not a dedicated Nexar lifecycle query in this release. Icecat retains source
metadata and downloads only user-selected images/documents.

## Licenses

Open Food Facts database/content licenses and image CC BY-SA attribution are
recorded in the normalized product and imported provenance. Keep source references
and required attribution when redistributing data/media; ODbL obligations may apply
to derivative databases. The plugin's MIT license does not relicense provider data.

For Icecat, UPCitemdb, EAN-DB and Nexar, account/brand terms control caching, image
use, document copying and redistribution. Result caching defaults off for these
providers. Local image/PDF downloads require administrator enablement, a selected
candidate, an exact host allowlist and a user's explicit rights confirmation.
Linked datasheets are the simpler default. Audit metadata on an imported part
retains the selected source record; use only sources whose terms permit this.

## Add a provider

1. Add a module in `providers/`, subclass `Provider`, set a unique `slug` and the
   supported lookup `modes`, and implement `search(Query) -> list[Product]`.
2. Decorate the class with `register` and import the module in `providers/__init__.py`.
   Generic settings are then created automatically from the registry.
3. Keep provider URLs fixed in the adapter; pass identifiers as encoded parameters
   or GraphQL variables. Reuse `Transport` for bounded, redacted error handling.
4. Return normalized products through `self.product(...)`, including provenance,
   source URL, media terms and useful raw product metadata.
5. Add fixtures and failure-mode tests; document terms, capabilities and live-test
   status. Do not enable new providers by default.

No search engine edits or second InvenTree plugin installation are necessary.
