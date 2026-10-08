# Regression benchmark

Fixtures and questions from the 8 October 2026 regression report (`eval/regression/cases.jsonl`).

| Metric | Result |
|---|---|
| Ingestion (valid accepted, invalid rejected, titles) | 10/10 |
| Facet coverage (parts of a question with a supporting passage) | 74/74 (100%) |
| Questions with every facet covered | 48/48 |
| Compound questions fully covered | 20/20 |
| Unanswerable questions stopped before the LLM (the rest must be refused by it) | 3/10 |
| Median retrieval latency | 1685 ms |

## Ingestion

| Case | Result | Detail |
|---|---|---|
| pdf-ingest | pass | title 'Aurora Quay Berth Allocation Plan 2026', 3 sections |
| docx-ingest | pass | title 'Sable Ridge Tunnel Gas Safety Procedure', 7 sections |
| md-ingest | pass | title 'Ember Canal Lock Operations Guide', 13 sections |
| txt-ingest | pass | title 'Mont Rivière Upper-Air Station', 10 sections |
| csv-reject | pass | rejected: 'tidal_grid_headerless.csv' has '48' as a column name. The first row looks like data: add a header row with a name for each column. |
| html-ingest | pass | title 'HT-NAMES: Reserved Names for Harbour Telemetry', 8 sections |
| live-pdf-ingest | pass | title 'Aurora Quay Polar Research Station', 3 sections |
| live-docx-ingest | pass | title 'Sable Ridge Observatory Field Manual', 13 sections |
| live-md-ingest | pass | title 'Ember Canal Control Handbook', 10 sections |
| live-txt-ingest | pass | title 'Mont Rivière Aerial Station Log', 11 sections |

## Questions

| Case | Facets covered | Sources sent | Latency | Answer |
|---|---|---|---|---|
| pdf-allocation | 1/1 | 2 | 1182 ms | - |
| pdf-percent | 1/1 | 2 | 1085 ms | - |
| pdf-cross-page | 2/2 | 2 | 1974 ms | - |
| pdf-refuse | FAIL: 2 sent | 2 | 467 ms | - |
| docx-table | 1/1 | 1 | 487 ms | - |
| docx-header | 1/1 | 4 | 1378 ms | - |
| docx-footer | 1/1 | 1 | 991 ms | - |
| docx-list | 1/1 | 1 | 825 ms | - |
| docx-conditional | 2/2 | 2 | 2143 ms | - |
| docx-reentry | 1/1 | 1 | 1190 ms | - |
| docx-refuse | FAIL: 6 sent | 6 | 340 ms | - |
| md-table | 1/1 | 6 | 351 ms | - |
| md-code | 1/1 | 1 | 885 ms | - |
| md-compound | 4/4 | 4 | 1918 ms | - |
| md-isolated | 1/1 | 1 | 956 ms | - |
| md-calc | 1/1 | 2 | 1410 ms | - |
| md-refuse | FAIL: 6 sent | 6 | 984 ms | - |
| txt-accents | 1/1 | 6 | 511 ms | - |
| txt-compound | 2/2 | 6 | 895 ms | - |
| txt-checklist | 1/1 | 2 | 1179 ms | - |
| txt-conditional | 2/2 | 3 | 1339 ms | - |
| txt-calc | 1/1 | 1 | 1017 ms | - |
| txt-refuse | refused | 0 | 592 ms | - |
| html-focused | 1/1 | 1 | 1031 ms | - |
| html-compare | 2/2 | 4 | 4713 ms | - |
| html-modal-words | 1/1 | 6 | 1256 ms | - |
| html-refuse | refused | 0 | 1360 ms | - |
| live-pdf-1 | 2/2 | 3 | 3238 ms | - |
| live-pdf-2 | 1/1 | 1 | 1170 ms | - |
| live-pdf-3 | 2/2 | 1 | 5074 ms | - |
| live-pdf-4 | 2/2 | 1 | 2418 ms | - |
| live-pdf-5 | FAIL: 2 sent | 2 | 1461 ms | - |
| live-docx-1 | 2/2 | 7 | 4574 ms | - |
| live-docx-2 | 2/2 | 2 | 8019 ms | - |
| live-docx-3 | 1/1 | 1 | 4520 ms | - |
| live-docx-4 | 1/1 | 2 | 2090 ms | - |
| live-docx-5 | 2/2 | 2 | 2384 ms | - |
| live-docx-6 | 2/2 | 3 | 4759 ms | - |
| live-docx-7 | refused | 0 | 3653 ms | - |
| live-md-1 | 1/1 | 2 | 1685 ms | - |
| live-md-2 | 1/1 | 1 | 2080 ms | - |
| live-md-3 | 2/2 | 1 | 2086 ms | - |
| live-md-4 | 3/3 | 4 | 2332 ms | - |
| live-md-5 | 1/1 | 2 | 1539 ms | - |
| live-md-6 | FAIL: 3 sent | 3 | 4866 ms | - |
| live-txt-1 | 1/1 | 5 | 7390 ms | - |
| live-txt-2 | 2/2 | 2 | 5374 ms | - |
| live-txt-3 | 1/1 | 3 | 1310 ms | - |
| live-txt-4 | 1/1 | 1 | 1636 ms | - |
| live-txt-5 | 2/2 | 7 | 2153 ms | - |
| live-txt-6 | 1/1 | 3 | 4004 ms | - |
| live-txt-7 | 1/1 | 3 | 2227 ms | - |
| live-txt-8 | FAIL: 4 sent | 4 | 1492 ms | - |
| live-csv-1 | 1/1 | 2 | 10209 ms | - |
| live-csv-2 | 4/4 | 5 | 2961 ms | - |
| live-csv-3 | 2/2 | 4 | 5780 ms | - |
| live-csv-4 | 3/3 | 4 | 4907 ms | - |
| live-csv-5 | FAIL: 4 sent | 4 | 3103 ms | - |
