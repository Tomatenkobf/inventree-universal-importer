# Testing and acceptance

The package includes unit, frontend interaction and actual InvenTree ORM/API tests.
Local execution uses Python 3.12, the selected upstream tags' pinned backend
requirements, SQLite, and no production inventory. See `COMPATIBILITY.md` for the
recorded results and `validation/` in the delivery bundle for logs.

## Test layers

- `pytest`: GTIN validation, manufacturer/MPN/variant matching, provenance/conflicts,
  CSV parsing and formula escaping, commercial provider response fixtures,
  authentication failures, missing credentials, response limits, timeout/429
  handling, cache isolation, partial results, URL/DNS/redirect protections and
  exact-version detection. No commercial requests are sent by unit tests.
- `frontend/npm test`: safe rendering of external strings, search, preview,
  explicit confirmation and the InvenTree 1.6 route's server-subpath context.
  TypeScript is checked before every asset build. These are DOM tests, not a full
  native-shell browser or camera test.
- `tests.integration`: plugin discovery, real URL resolution, packaged static asset
  discovery, permissions, create/enrich, no stock creation, GTIN and specification
  parameters, category mapping, manufacturer relation, stale previews, duplicate
  changes and idempotency, transaction rollback, image storage, corrupt-image
  rejection, linked datasheets, cross-instance rate gate, owner-bound background
  job execution and removal of stored confirmation tokens.
- `tools/integration_check.py`: initialize a fresh core database, simulate administrator
  activation through PluginConfig, enable App/URL/UI integration, apply plugin-owned
  migrations, verify normal Django/plugin startup, run system checks, collect static
  files and execute integration tests.
  It generates a temporary configuration and does not use your deployment's
  `INVENTREE_*` environment values.

InvenTree 1.5.6 and 1.5.7 have identical pinned backend requirement files in the
checked tags. InvenTree 1.6.3 was tested with its own separate dependency environment.
GitHub Actions definitions are included but were not run on a remote repository.

## Deployment smoke checklist — still required

Run this against staging before calling the release production-ready:

1. Verify plugin discovery, migration and frontend serving in the real deployment.
2. Open the panel/dashboard under 1.5.x or navigation page under 1.6.3 in light and
   dark themes; test with a normal authorized user and with a denied user.
3. Enable only demo; search the sample barcode, preview, import, reopen the part,
   search again, and confirm duplicate detection and manufacturer/parameter mapping.
4. Disable demo and configure at least one live provider. Confirm successful
   lookup of a known product, actual metadata and image display. Repeat with a
   missing product, invalid barcode and provider authentication failure.
5. Verify each paid provider with its actual account entitlement and license terms.
6. Check selected image/PDF storage, host allowlists and media serving. Verify
   attribution and source metadata on the imported part.
7. Test enrichment conflicts and a concurrent edit after preview. Exercise
   concurrent imports on the production database engine; SQLite tests do not
   certify PostgreSQL/MySQL locking or behavior against other plugins' writes.
8. Start the real worker; queue reviewed rows, inspect partial failure reports,
   test worker interruption/recovery, and verify permissions revoked before execution.
9. Test your USB scanner, and camera scanning where the browser supports it.
10. Test a backup restore/rollback and record the exact passing deployment versions.

## Provider live test result

No commercial credentials were available. Direct Open Food Facts and UPCitemdb
requests attempted from this execution environment failed with network/transport
errors. Consequently **successful live lookup is not an accepted test result** for
this delivery. Mock adapter tests passing does not change that status.

## CI and future versions

The test workflow runs pinned 1.5.6, 1.5.7 and 1.6.3 jobs and repeats weekly.
New stable versions are evaluated by adding an explicit matrix entry and running
its isolated environment. Runtime permission to run, backend integration success
and deployment acceptance are distinct states. Update the matrix/documentation
only on observed evidence; never use an unbounded future-version claim.
