# Scope against the requested project

| Area | Delivered | Boundary / pending acceptance |
| --- | --- | --- |
| One installable plugin | Python entry point, App/URL/UI/Settings mixins, prebuilt assets | Install/activate in user's deployment |
| 1.5.6 native UI | Part/category panel and dashboard widget | That version has no custom native route hook |
| 1.6 native page | Version 1.6.3 route and navigation integration | Browser end-to-end check still required |
| Search identifiers | GTIN/UPC/EAN; MPN + manufacturer; text; IPN existing lookup | Coverage depends on catalog |
| Open Food Facts | Real documented HTTP adapter and fixtures | Live request did not succeed here |
| Icecat | Documented account/GTIN/brand-code adapter and fixtures | Real account and brand entitlement test |
| UPCitemdb / EAN-DB / Nexar | Request/authentication/normalization implementations and fixtures | No successful authenticated live tests |
| GS1 | Documented contract boundary; no guessed endpoint | Specific authorized API contract required |
| Normalization/merging | Validated GTIN, strong identity matching, provenance and conflicts | No fuzzy-name auto-merge; unknown packaging stays separate |
| Duplicate checks | Imported GTIN metadata, configured GTIN parameters, manufacturer part, IPN, name-only warning | Arbitrary custom identifier formats need an adapter; other writers do not take the plugin lock |
| Import/enrichment | Signed preview, selected fields, explicit overwrites, transactions and idempotency | Production DB concurrency/load validation |
| Parameters/categories | Existing template/category selection and maps | Automatic category/template creation intentionally unavailable |
| Images/documents | Candidates, links, selected bounded local image/PDF download | Licensing/account approval and real media host checks |
| Stock/suppliers | No implicit stock, quantities, supplier SKU or supplier creation | Explicit stock-import mode is not implemented |
| CSV | Header mapping, validation, per-row review/retry, approved background batches, reports | 1 MB / 200 rows; 50 reviewed items/job; no unattended large-catalog lookup |
| Background tasks | Existing InvenTree worker, owner-scoped job state and recovery | Real worker deployment test |
| Caching/rates | Django result cache, plugin DB cooldowns, partial results | Account-wide daily/monthly quota tracking is not provided |
| UI scanning | Keyboard scanners and optional browser BarcodeDetector | Real scanner/camera test; manual entry always available |
| Tests/CI/package/docs | Automated local tests, pinned CI matrix, upgrade/rollback docs, wheel/sdist | Remote CI and deployment acceptance not executed |

This candidate implements the core review-and-import workflow. It does not meet all
production acceptance criteria yet, particularly successful live database lookup
and end-to-end validation in the user's installation. No production records were
modified during development.
