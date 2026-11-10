# Release 0.1.0rc4

Allows stable InvenTree 1.5.6 through 2.0.0 inclusive. Untested versions show a
warning but can import. This cannot guarantee compatibility with future API changes.
Versions above 2.0.0 and prereleases remain blocked. No schema changes.

Wait until any current InvenTree core upgrade/migrations have finished before
upgrading the plugin. This change does not repair a held static-file lease.

Extract the delivery and copy the CONTENTS of project/ into your existing Git
checkout, preserving .git. If that checkout predates your browser-based CI fix,
first run git pull --ff-only before copying. Stop on conflicts rather than force-push.
The included workflows already preserve the Ubuntu 24.04 runner fix.

From the checkout:

```bash
git rm --ignore-unmatch inventree_universal_importer/static/plugins/universal-importer/importer.js
git add -A
git diff --cached --stat
git commit -m "Allow stable InvenTree versions through 2.0.0"
git push
```

Wait for Actions to pass. Create a NEW GitHub pre-release tag v0.1.0rc4 targeting
that commit. Attach the wheel, source tarball and SHA256SUMS.txt from release/.
Do not move the rc3 tag. No GitHub push was performed by the assistant.

In InvenTree Install Plugin:
Package Name: inventree-universal-importer
Source URL: git+https://github.com/Tomatenkobf/inventree-universal-importer.git@v0.1.0rc4
Version: leave empty

Confirm installation during an appropriate maintenance window. Verify installed
plugin version 0.1.0rc4, then reload your browser. Existing provider settings remain.
Docker persistence and consistent web/worker versions are still required.

Checks for rc4: 74 Python unit tests passed, Ruff F checks passed, distribution
build and wheel content checks passed. Tests cover inclusive endpoints, future
minor versions, out-of-range versions, prereleases, and non-blocking warnings.
No new full host integration or live-provider test was performed for this policy change.
