# Compatibility — 0.1.0rc3

Target added: InvenTree 1.7.0, commit `365245ed73eb469cf80578856947ce92eca8b271`.
The metadata ceiling is 1.7.0. Exact runtime versions allowed are 1.5.6, 1.5.7,
1.6.3 and 1.7.0. Other releases, including prereleases, remain unverified and blocked.

The JavaScript asset is now `inventree_universal_importer/static/importer.js`.
InvenTree's collector supplies the `plugins/universal-importer/` destination prefix.
The integration test now calls that collector and reads the resulting asset;
the previous static finder test did not check this deployment path.

On 2026-11-04, fresh migration, normal startup, system checks and static collection passed on 1.7.0. Of 18 integration tests, 17 passed initially; the remaining test assumed the host did not cache request bodies. After correcting that test setup, its targeted rerun passed. Unit tests: 61 passed; frontend tests: 2 passed. See the delivery's VALIDATION.txt for details. The older
results below are historical, not claims of rerunning rc3 on every older release.
CI now includes 1.7.0 alongside the three older versions. No full native-shell
browser or production-server test is claimed.

# Historical rc1 validation

Status recorded 2026-10-29. Exact tagged source was inspected and exercised.
Automated backend compatibility is distinct from production acceptance.

| InvenTree | Exact source commit | Automated backend integration | Native UI entry |
| --- | --- | --- | --- |
| 1.5.6 | `284a670413cc544b899f6a60713b9676beccb8ea` | 16 tests passed | Part/category panel and dashboard widget |
| 1.5.7 | `2ca0d0e55b08e138342b20fccfa8307fad25a02c` | 15 tests passed | Part/category panel and dashboard widget |
| 1.6.3 | `221af32fdb4382f29c351d9dd9b39992bfaf8d12` | 16 tests passed | Panel/widget plus navigation page |


Fresh-database migration, normal Django/plugin startup, system checks and static
collection passed on all three versions. Unit tests: 61 passed. Frontend DOM tests:
2 passed. The final PDF-download test was additionally run on 1.5.6 and 1.6.3;
1.5.7 ran the preceding 15-test integration suite.

Local tests use Python 3.12, SQLite and each selected release's backend requirements.
The 1.5.6 and 1.5.7 pinned requirements are identical. Version 1.6.3 uses a separate
virtualenv. Fresh-install tests explicitly disable SQLite WAL in their temporary
configuration because the execution workspace's file-backed WAL behavior was not
reliable. This test configuration is not a recommendation to change production.

The broad plugin metadata uses `MIN_VERSION=1.5.6` and `MAX_VERSION=1.6.3`.
An additional exact runtime allowlist prevents an intervening or future untested
release from silently accepting imports. Startup and the UI expose compatibility
status; unsupported plugin loading is handled through InvenTree's version mechanism.

## API boundaries checked

- `plugin.InvenTreePlugin` and official App/Settings/URL/UserInterface mixins.
- `setup_urls`, `get_ui_panels`, `get_ui_dashboard_items`, static packaging.
- `get_ui_routes` and navigation only for the evaluated 1.6.3 frontend.
- Part name/description/IPN/category/image/metadata; Company manufacturer flag;
  ManufacturerPart part/manufacturer/MPN relationship.
- Generic `common.Parameter` + ContentType + ParameterTemplate.
- `common.Attachment` model type `part`, model ID, link, file and upload user.
- InvenTree `offload_task` with the already-configured background worker.

The integration uses validated ORM operations, not direct SQL or core schema
patches. InvenTree model interfaces are not universally stable; they are isolated
in `inventree_adapter/` and must be retested for each supported version.

## What these results do not prove

There has been no full browser end-to-end run of InvenTree's own application shell,
no real camera/USB hardware test, no commercial account live test, no successful
live provider lookup from the build environment, and no PostgreSQL/MySQL production
concurrency/load test. A real worker-process deployment smoke test is also pending.
GitHub Actions files are supplied; no remote Actions run is claimed.

Use staging and complete `docs/testing.md` before production. See
`docs/REQUIREMENTS-STATUS.md` for remaining scope. Do not extend the exact allowlist
or claim future releases work without testing their real dependencies and APIs.
