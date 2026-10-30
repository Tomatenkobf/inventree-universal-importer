# Architecture and security boundaries

`plugin.py` registers only official InvenTree mixins: Settings, URL, UI and App.
`core/` and `providers/` have no InvenTree model dependencies. `inventree_adapter/`
contains all part/company/parameter/attachment ORM integration, permissions,
compatibility and shared quotas. Model operations are intentionally isolated:
InvenTree does not promise a stable Python model API across every release.

## Request flow

Search validates identifiers, checks existing parts, looks for permitted cached
responses, queries capable sources and returns normalized records with conflicts.
It creates no parts, companies, categories or stock.

Preview validates selected edits and captures the existing part/parameters/
manufacturer links/attachments plus the duplicate set. Django signs this snapshot
with a timestamp, user ID and random nonce. Import requires that signature, current
permissions, explicit confirmation and (when applicable) a separate-part approval.

Inside a database transaction the importer locks its PluginConfig row, rechecks
part state and duplicates, then applies approved changes using normal model
validation and saves. Idempotency receipts are held for longer than the 30-minute
signature lifetime. Plugin imports serialize against each other; writes from core
InvenTree or other plugins do not acquire this lock. Such external races still
need deployment-level coordination and database-specific testing.

## Database and media

The plugin owns two tables: request cooldowns and reviewed background import jobs.
No raw SQL, core table definition change, custom core field or external database is
required. The database-backed cooldown works across web/worker processes even if
Django uses a process-local result cache. A provider failure returns partial results.
Quota enforcement is conservative request spacing, not a replacement for tracking
an account's daily/monthly allowance.

Selected media is fetched before part creation. Downloads allow only configured
exact HTTPS hosts on port 443. Every DNS answer must be public. The connection is
pinned to a validated address while preserving TLS hostname verification/SNI.
Redirects and environment proxies are disabled. Images are capped at 5 MB and
20 megapixels, checked with Pillow and re-encoded to JPEG; PDF input is capped at
10 MB and checked with pypdf. Downloaded PDFs are attachments, not executed or
server-rendered by the plugin. This is format validation, not malware scanning.

Newly written main media files are deleted on a failed database transaction where
possible. Object storage and database commits are not a distributed transaction;
a process crash/storage failure can leave orphaned media, which should be handled
by normal media maintenance. Existing images are never replaced.

## Access and secrets

DRF authentication is required on all endpoints. The host's standard authentication
and CSRF behavior are preserved. Search needs `part.view_part`; creation/enrichment
need `part.add_part` / `part.change_part`. Related writes check company,
manufacturer-part, parameter and attachment permissions. Every queued row is
executed as its original active user with fresh permission checks.

Job lookup/recovery is constrained to its owner. Provider keys remain server-side,
are marked protected in InvenTree settings, and never enter frontend responses or
cache keys in plaintext. Protected settings mask display; secure the database,
backups and administrator access separately. No secrets were bundled here.

External strings are rendered with DOM text nodes, not HTML interpolation. CSV
report cells starting with formula-significant characters are escaped. Provider
failures use fixed error codes rather than exception text or raw response bodies.

## Boundaries requiring deployment verification

The automated local tests do not establish browser/worker/PostgreSQL/MySQL load
behavior. Python socket timeouts bound individual operations, with an additional
budget checked between providers; DNS resolution is still subject to host resolver
behavior. API requests use fixed provider hosts and direct HTTPS, so deployments
requiring an outbound HTTP proxy need a reviewed transport adaptation. Media proxy
bypass is intentional to preserve the DNS-pinning security model.
