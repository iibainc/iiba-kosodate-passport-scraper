# PLAN

| Priority | Status | Task | Notes |
| --- | --- | --- | --- |
| 1 | DONE | Geocoding disabled mode still requires an API key causing BatchOrchestrator initialization to crash in local/dev environments. | `GEOCODING_ENABLED=false` (default in `.env.development`) now bypasses geocoding by skipping service initialization and having the job treat geocoding as optional, so local/dev runs no longer fail. |
| 2 | DONE | `.env.development` is missing the required `GCS_BUCKET_NAME` / `GCS_CSV_PREFIX`, so `Settings()` validation fails right after running `make dev-setup`. | Added safe stub values (`local-dev-bucket` + `csv_exports/`) so `Settings()` validation succeeds as soon as `.env.development` is copied. |

