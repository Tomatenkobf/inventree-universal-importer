# Troubleshooting

| Symptom | Check |
| --- | --- |
| Plugin missing | Install into the web/worker virtualenv; verify the `inventree_plugins` entry point; enable server plugin support; restart both services |
| Panel/widget missing | Enable UI integration and the plugin; grant part-view permission; open a part/category panel or add the dashboard widget |
| No standalone page on 1.5.6 | Expected: custom routes are absent from that version; use the panel/widget |
| API redirects instead of JSON | Enable plugin URL support and restart; check reverse-proxy subpath configuration |
| Missing plugin table | Enable App support and plugin activation, restart, then run migrations in the correct environment |
| JavaScript 404 | Collect static assets after installation; verify App support and web static serving |
| No provider results | Read per-provider errors; check enabled modes, actual catalog coverage, credentials and egress |
| `local_rate_limit` / `rate_limited` | Wait for the interval / retry-after; do not loop retries or increase quotas blindly |
| Icecat denies access | Check username/tokens, approved account access and brand/catalog entitlements |
| Nexar GraphQL error | Confirm Supply entitlement and the current schema/account configuration |
| Nonempty field blocked | Review current values and explicitly approve that field in the overwrite list |
| Preview rejected | Expired, another user, changed part or changed duplicate set: generate a fresh preview |
| Media download rejected | Exact host allowlist, public DNS, HTTPS, format/size, rights confirmation and `ALLOW_MEDIA` |
| Background job remains queued | Start the existing InvenTree worker with this exact plugin version and migrate its environment |
| Partial job failure | Review failed rows again; completed rows are not automatically repeated |
| Concurrent update conflict | Refresh the preview and retry; do not bypass duplicate checking |

For diagnosis, record plugin/InvenTree versions, provider name, fixed error code and
job ID. Never send API keys or raw authenticated request URLs. Outbound API requests
and media downloads do not use environment HTTP proxies in this release.

The demo provider is the deterministic way to separate integration problems from
external API access problems. Its sample barcode is `4006381333931`; turn it off
before using real inventory lookups to avoid synthetic matches.
