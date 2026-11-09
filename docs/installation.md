# Installation

Use staging first. This release has not been published to PyPI: a bare
`pip install inventree-universal-importer` must not be assumed to retrieve this
code. Install the wheel supplied in `dist/` or a trusted, pinned source checkout.
Python 3.12 or later is required by the initial InvenTree target.

## Persistent installation with Docker Compose

Service names, container paths and volume layout depend on your deployment.
The names below are placeholders, not an assumed Compose structure.

1. Put the supplied wheel in a persistent directory mounted read-only into both
   the InvenTree web and worker containers, for example an administrator-selected
   `/plugins-wheels/` container directory.
2. Add this **container-visible absolute path** as a line in the persistent plugin
   requirements file configured by `INVENTREE_PLUGIN_FILE`:

   ```text
   /plugins-wheels/inventree_universal_importer-0.1.0rc3-py3-none-any.whl
   ```

   Preserve all existing lines. The file is normally called `plugins.txt`; its
   actual location is controlled by your installation.
3. Enable server plugin loading (`INVENTREE_PLUGINS_ENABLED=true`, or the matching
   configuration option). Use InvenTree's **Check Plugins on Startup** setting to
   reinstall requirements when containers are recreated, or build a pinned custom
   image installing the same wheel into both web and worker environments.
4. From the normal InvenTree backend working directory, install plugin requirements:

   ```sh
   docker compose exec WEB_SERVICE invoke plugins
   docker compose exec WORKER_SERVICE invoke plugins
   ```

   If either service is unavailable or lacks `invoke`, use the deployment's
   supported maintenance container or custom-image build process. Do not install
   into an unrelated system Python.
5. Restart both services so the entry point is discovered. In the administration
   settings enable plugin **App**, **URL** and **User Interface** support, then
   enable **Universal Product Importer**. Apply its migrations before the next
   normal web/worker startup; a maintenance container can run while those services
   are stopped.
6. With user traffic paused and the worker stopped, run the normal database and
   static-file maintenance commands in the same environment:

   ```sh
   docker compose run --rm WEB_SERVICE python manage.py migrate --noinput
   docker compose run --rm WEB_SERVICE python manage.py collectstatic --noinput
   ```

   `manage.py` must be addressed from your backend directory; use its absolute path
   if your container working directory differs. In standard InvenTree Compose
   deployments, `docker compose run --rm WEB_SERVICE invoke update` is the supported
   combined maintenance alternative; review its deployment-specific update scope.
   The migration creates only
   `inventree_universal_importer` tables. No core schema patch is made.
7. Restart web and worker, then perform the staging smoke test. The worker is only
   needed for queued batch execution; single-part import is synchronous.

Do not rely on an ad hoc pip installation inside an ephemeral container. Keep the
wheel and the plugin requirement file on persistent storage or in a reproducible
image build. Preserve the InvenTree database and media using its normal volumes.

## Direct Python / virtualenv installation

Activate the **same virtualenv as the InvenTree web server and worker**:

```sh
python -m pip install /absolute/path/inventree_universal_importer-0.1.0rc3-py3-none-any.whl
```

Alternatively, from the extracted source project:

```sh
python -m pip install .
```

Then follow steps 5–7 above using your service manager and backend directory:

```sh
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Add the trusted wheel path or a pinned package source to InvenTree's persistent
plugin requirements file, so your deployment's `invoke update` / `invoke plugins`
workflow reinstalls the intended version. Ensure web and worker run the same
plugin version.

## Activation and first test

In plugin settings:

- `ENABLED = true`
- `DEMO_ENABLED = true`
- `OPENFOODFACTS_ENABLED = false` for the offline smoke test
- `ALLOW_MANUFACTURER_CREATE = false` initially
- `ALLOW_MEDIA = false` initially

Use the dashboard's widget configuration to add **Universal Product Importer**,
or open its panel on an existing part/category. On 1.6.3 use the navigation item.
Search `4006381333931`, review the synthetic sensor and create a staging part.
The name, description and GTIN metadata import without manufacturer creation.
Search again: the existing part must be reported. Re-submit a completed signed
confirmation: it must return the same part, not create another one.

Now switch off the demo provider, configure real sources, and continue with
[testing.md](testing.md). Protect the plugin settings database and its backups:
InvenTree's `protected` setting flag masks secret fields, but does not itself
promise encryption at rest.

Official versioned references:
- https://docs.inventree.org/en/1.5.x/plugins/install/
- https://docs.inventree.org/en/1.5.x/plugins/mixins/app/
- https://docs.inventree.org/en/1.5.x/plugins/mixins/ui/
