# Upload rc2 to your GitHub repository

The archive contains `project/` (repository files) and `release/` (built packages).
Only copy the CONTENTS of `project/` into the repository. `pyproject.toml` must be
at repository root. The prebuilt JavaScript is included; Node is not needed to
install the plugin. No API credentials or InvenTree databases are included.

## Recommended WSL route

Extract this delivery under `~/inventree-plugin-rc2`. Clone your GitHub repository
into a separate directory (works whether it is empty or has an initial README):

```bash
cd ~
git clone https://github.com/Tomatenkobf/inventree-universal-importer.git inventree-plugin-github
cp -a ~/inventree-plugin-rc2/project/. ~/inventree-plugin-github/
cd ~/inventree-plugin-github
git status --short
git add .
git diff --cached --stat
git commit -m "Release 0.1.0rc2: fix parsed request body handling"
git push -u origin HEAD
```

Review files before committing; this replaces same-named starter files. Never copy
`~/inventree-test`, its virtual environment, config, database or media. Do not use
force push. If Git needs an identity, set your name and GitHub email with local
`git config user.name` and `git config user.email`. HTTPS authentication requires
GitHub-supported credentials (a token or credential manager), not your GitHub
password. Keep tokens out of URLs, files and chat. If authentication is inconvenient,
use GitHub Desktop to clone, copy project contents, commit and push instead.

Wait for GitHub Actions checks to pass. Then create the release via GitHub:
Releases -> Draft a new release -> new tag `v0.1.0rc2` targeting your uploaded
commit. Mark it as a pre-release. Attach the wheel and source tarball from
`release/`. Publish the release. Do not reuse or move this tag for later fixes.

## InvenTree installer (1.5.6)

Only after that tag exists, enter:

- Package Name: `inventree-universal-importer`
- Source URL: `git+https://github.com/Tomatenkobf/inventree-universal-importer.git@v0.1.0rc2`
- Version: leave blank (the Git URL pins the release)

The server needs Git, access to GitHub/dependency sources, and permission to install
plugins. A private repository additionally requires server-side authentication
configured by IT; never put a token in this form. Public visibility makes code
public, so choose visibility intentionally.

## IT handoff

Back up database, media and configuration. This remains a release candidate.
Confirm plugin App, URL and UI support are enabled. Install the same pinned plugin
in web and worker environments, activate it, run migrations and collectstatic in
the deployment's normal maintenance environment, then restart both services.
Docker installations must preserve the plugin requirements file and reinstall it
on container recreation, or bake it into a maintained image. A successful web
installation alone does not prove persistence or worker consistency. See
`docs/installation.md`; exact Compose service names depend on your deployment.

rc2 has no new schema migrations compared with rc1, but first installation still
requires the existing plugin migration. Run a single import without/with an image
and a repeated lookup before broader use. Keep demo disabled for real imports.

## Validation

Historical validation files, if supplied separately, concern rc1. rc2 adds two
regression tests covering already-parsed bodies and oversized declared requests.
See the delivered validation summary for the exact checks rerun for rc2. User
reports confirm local provider imports, but do not establish production readiness.

References:
https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github
https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository
