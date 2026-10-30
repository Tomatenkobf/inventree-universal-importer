# 0.1.0rc2

- Fix RawPostDataException when InvenTree authentication has already parsed a request.
- Preserve declared request-size validation without rereading the raw stream.
- Add regression coverage for parsed requests and oversized requests.
- No database schema changes.

# Changelog

## 0.1.0rc1 — 2026-10-29

Initial staging candidate: official plugin registration; 1.5 panels/dashboard and
1.6 route; provider adapters and offline demo; GTIN/MPN/text search; conservative
merging/provenance; signed previews; transactional import/enrichment; duplicate and
permission checks; controlled media; reviewed CSV and worker execution; plugin-owned
shared cooldown/job tables; source packaging and CI.

Not production-certified. GS1, commercial live account verification, full native
browser/camera testing and database-specific concurrency/load validation remain
outside the verified release scope. See the compatibility and testing documents.
