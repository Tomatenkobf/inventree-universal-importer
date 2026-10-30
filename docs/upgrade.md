# Upgrade and rollback

## Before an upgrade

1. Back up the InvenTree database, media, configuration and plugin requirement file.
2. Record both InvenTree and plugin versions. Preserve the previous wheel.
3. Finish or stop queued jobs. Use a cloned staging database/media set.
4. Check `COMPATIBILITY.md`. A version inside the broad plugin metadata bounds is
   not automatically accepted: the runtime also checks exact allowed versions.
5. Run unit, UI and the actual-tag integration tests. Then perform the deployment
   smoke checklist. Do not mark a future version supported merely because it starts.

## Plugin update

Update the persistent wheel/requirements entry, install it in both web and worker
Python environments, stop normal traffic/workers, run `manage.py migrate` and
`manage.py collectstatic`, then restart both services. For containers, rebuild the
pinned image or use the persistent plugin requirements startup mechanism. Clear
browser caches if old frontend assets remain loaded. Do not edit core files.

## InvenTree update

Create a separate virtualenv/container using the new stable tag's own dependencies.
Run `tools/integration_check.py` against that exact source tag. Review model-field,
permission and UI-hook changes in the adapter and plugin integration. The providers
and matching engine should remain unchanged unless their own APIs changed.

Only after passing tests and reviewing behavior should you update the exact
allowlist, `TESTED_VERSIONS`, plugin version constraints and CI matrix. The weekly
CI run rechecks the pinned matrix; newly published versions must be explicitly
added for evaluation. It never silently expands support or updates production.

## Rollback

Disable the plugin first if it prevents normal use, then restore the previous
pinned package in both services and collect static files again. Keep media and
plugin-owned tables until the rollback is verified; uninstalling code is not a
reason to delete inventory.

If a future plugin/InvenTree migration is not backward compatible, restore the
**matching pre-upgrade database and media backup** along with the old software.
Installing an older wheel does not reverse a schema migration. Do not manually
alter core tables. Restart web/worker together and repeat the offline smoke test.

This initial plugin migration only creates its own rate/job tables. Imported
parts, manufacturer records, parameters and attachment records are normal
InvenTree objects; disabling/uninstalling the plugin does not remove them.
