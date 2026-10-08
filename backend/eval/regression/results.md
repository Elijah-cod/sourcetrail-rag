# Regression benchmark

Fixtures and questions from the 8 October 2026 regression report (`eval/regression/cases.jsonl`).

| Metric | Result |
|---|---|
| Ingestion (valid accepted, invalid rejected, titles) | 7/7 |
| Facet coverage (parts of a question with a supporting passage) | 37/37 (100%) |
| Questions with every facet covered | 25/25 |
| Compound questions fully covered | 8/8 |
| Unanswerable questions stopped before the LLM (the rest must be refused by it) | 3/6 |
| Median retrieval latency | 1125 ms |

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
| pdf-allocation | 1/1 | 2 | 2257 ms | - |
| pdf-percent | 1/1 | 2 | 1391 ms | - |
| pdf-cross-page | 2/2 | 3 | 4118 ms | - |
| pdf-refuse | FAIL: 1 sent | 1 | 318 ms | - |
| docx-table | 1/1 | 1 | 571 ms | - |
| docx-header | 1/1 | 4 | 1405 ms | - |
| docx-footer | 1/1 | 1 | 971 ms | - |
| docx-list | 1/1 | 1 | 809 ms | - |
| docx-conditional | 2/2 | 1 | 3450 ms | - |
| docx-reentry | 1/1 | 1 | 1090 ms | - |
| docx-refuse | FAIL: 6 sent | 6 | 509 ms | - |
| md-table | 1/1 | 6 | 459 ms | - |
| md-code | 1/1 | 1 | 1847 ms | - |
| md-compound | 4/4 | 4 | 4636 ms | - |
| md-isolated | 1/1 | 1 | 978 ms | - |
| md-calc | 1/1 | 2 | 1468 ms | - |
| md-refuse | refused | 0 | 809 ms | - |
| txt-accents | 1/1 | 6 | 476 ms | - |
| txt-compound | 2/2 | 3 | 3156 ms | - |
| txt-checklist | 1/1 | 1 | 1125 ms | - |
| txt-conditional | 2/2 | 2 | 10172 ms | - |
| txt-calc | 1/1 | 1 | 866 ms | - |
| txt-refuse | refused | 0 | 445 ms | - |
| csv-row | 1/1 | 1 | 2184 ms | - |
| csv-overdue | 4/4 | 3 | 665 ms | - |
| csv-total | 2/2 | 4 | 973 ms | - |
| csv-refuse | FAIL: 1 sent | 1 | 644 ms | - |
| html-focused | 1/1 | 1 | 1146 ms | - |
| html-compare | 2/2 | 4 | 7444 ms | - |
| html-modal-words | 1/1 | 6 | 1384 ms | - |
| html-refuse | refused | 0 | 1214 ms | - |
