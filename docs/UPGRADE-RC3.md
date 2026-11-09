# Upgrade to 0.1.0rc3 for InvenTree 1.7.0

This release raises the plugin version ceiling and exact runtime allowlist to
include 1.7.0. It also corrects the static package layout: InvenTree adds
`plugins/universal-importer/` itself when collecting plugin assets. The previous
layout duplicated that prefix and could cause a 404 in Docker installations.
No new database migration is introduced. Existing data/settings remain in place.

## Publish to your existing GitHub repository

Extract the delivery. Copy the contents of `project/` into your local clone of
https://github.com/Tomatenkobf/inventree-universal-importer.git
Preserve its `.git` directory. Review any local custom modifications before
replacing files. Delete the old asset from Git (the new asset is static/importer.js):

```bash
git rm --ignore-unmatch inventree_universal_importer/static/plugins/universal-importer/importer.js
git add -A
git diff --cached --stat
git commit -m "Support InvenTree 1.7.0 and fix automatic static collection"
git push
```

Wait for the repository Actions checks. Create a NEW pre-release tag `v0.1.0rc3`
on this commit. Attach the wheel, source archive and SHA256SUMS.txt from `release/`.
Do not modify the previous rc2 tag. This delivery has not been pushed to GitHub.

## Upgrade InvenTree

Use the same plugin installer that installed rc2:

- Package Name: `inventree-universal-importer`
- Source URL: `git+https://github.com/Tomatenkobf/inventree-universal-importer.git@v0.1.0rc3`
- Version: blank

Coordinate the maintenance window on a shared server. Confirm the plugin version
shows 0.1.0rc3, then activate/reload as needed and hard-refresh the browser. Confirm
the advertised `/static/plugins/universal-importer/importer.js` loads. No manual
JavaScript copy should be required with a working InvenTree plugin collector.
If it still returns 404, inspect collection/worker errors and shared static storage;
the package layout correction cannot fix a broken server volume configuration.

Test one search/import and a duplicate lookup. On 1.7.0 the importer also offers
a navigation page in addition to its panels/widget. Keep the same provider settings.
Docker persistence and consistent server/worker package versions remain deployment
requirements. Consult VALIDATION.txt for the exact scope verified locally.
