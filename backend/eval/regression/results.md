# Regression benchmark

Fixtures and questions from the 8 October 2026 regression report (`eval/regression/cases.jsonl`).

| Metric | Result |
|---|---|
| Ingestion (valid accepted, invalid rejected, titles) | 7/7 |
| Facet coverage (parts of a question with a supporting passage) | 37/37 (100%) |
| Questions with every facet covered | 25/25 |
| Compound questions fully covered | 8/8 |
| Unanswerable questions stopped before the LLM (the rest must be refused by it) | 3/6 |
| Median retrieval latency | 1166 ms |

## Ingestion

| Case | Result | Detail |
|---|---|---|
| pdf-ingest | pass | title 'Aurora Quay Berth Allocation Plan 2026', 3 sections |
| docx-ingest | pass | title 'Sable Ridge Tunnel Gas Safety Procedure', 7 sections |
| md-ingest | pass | title 'Ember Canal Lock Operations Guide', 13 sections |
| txt-ingest | pass | title 'Mont Rivière Upper-Air Station', 10 sections |
| csv-ingest | pass | title 'tidal grid', 10 sections |
| csv-reject | pass | rejected: 'tidal_grid_headerless.csv' has '48' as a column name. The first row looks like data: add a header row with a name for each column. |
| html-ingest | pass | title 'HT-NAMES: Reserved Names for Harbour Telemetry', 8 sections |

## Questions

| Case | Facets covered | Sources sent | Latency | Answer |
|---|---|---|---|---|
| pdf-allocation | 1/1 | 2 | 2341 ms | - |
| pdf-percent | 1/1 | 2 | 1366 ms | - |
| pdf-cross-page | 2/2 | 3 | 4177 ms | - |
| pdf-refuse | FAIL: 1 sent | 1 | 365 ms | - |
| docx-table | 1/1 | 1 | 527 ms | - |
| docx-header | 1/1 | 4 | 1447 ms | - |
| docx-footer | 1/1 | 1 | 1023 ms | - |
| docx-list | 1/1 | 1 | 877 ms | - |
| docx-conditional | 2/2 | 1 | 3337 ms | - |
| docx-reentry | 1/1 | 1 | 1068 ms | - |
| docx-refuse | FAIL: 6 sent | 6 | 471 ms | - |
| md-table | 1/1 | 6 | 465 ms | - |
| md-code | 1/1 | 1 | 1718 ms | - |
| md-compound | 4/4 | 4 | 4876 ms | - |
| md-isolated | 1/1 | 1 | 1034 ms | - |
| md-calc | 1/1 | 2 | 1475 ms | - |
| md-refuse | refused | 0 | 787 ms | - |
| txt-accents | 1/1 | 6 | 381 ms | - |
| txt-compound | 2/2 | 3 | 2965 ms | - |
| txt-checklist | 1/1 | 1 | 1166 ms | - |
| txt-conditional | 2/2 | 2 | 10188 ms | - |
| txt-calc | 1/1 | 1 | 928 ms | - |
| txt-refuse | refused | 0 | 502 ms | - |
| csv-row | 1/1 | 1 | 2395 ms | - |
| csv-overdue | 4/4 | 3 | 726 ms | - |
| csv-total | 2/2 | 4 | 1069 ms | - |
| csv-refuse | FAIL: 1 sent | 1 | 643 ms | - |
| html-focused | 1/1 | 1 | 1383 ms | - |
| html-compare | 2/2 | 4 | 7291 ms | - |
| html-modal-words | 1/1 | 6 | 1277 ms | - |
| html-refuse | refused | 0 | 1173 ms | - |
