# Regression benchmark

Fixtures and questions from the 8 October 2026 regression report (`eval/regression/cases.jsonl`).

| Metric | Result |
|---|---|
| Ingestion (valid accepted, invalid rejected, titles) | 7/7 |
| Facet coverage (parts of a question with a supporting passage) | 33/37 (89%) |
| Questions with every facet covered | 22/25 |
| Compound questions fully covered | 5/8 |
| Unanswerable questions stopped before the LLM | 3/6 |
| Median retrieval latency | 142 ms |

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
| pdf-allocation | 1/1 | 2 | 114 ms | - |
| pdf-percent | 1/1 | 2 | 120 ms | - |
| pdf-cross-page | 2/2 | 2 | 118 ms | - |
| pdf-refuse | FAIL: 1 sent | 1 | 106 ms | - |
| docx-table | 1/1 | 1 | 143 ms | - |
| docx-header | 1/1 | 4 | 142 ms | - |
| docx-footer | 1/1 | 1 | 137 ms | - |
| docx-list | 1/1 | 1 | 118 ms | - |
| docx-conditional | 2/2 | 1 | 181 ms | - |
| docx-reentry | 1/1 | 1 | 149 ms | - |
| docx-refuse | FAIL: 6 sent | 6 | 138 ms | - |
| md-table | 1/1 | 6 | 332 ms | - |
| md-code | 1/1 | 1 | 274 ms | - |
| md-compound | 3/4 | 3 | 308 ms | - |
| md-isolated | 1/1 | 1 | 248 ms | - |
| md-calc | 1/1 | 2 | 260 ms | - |
| md-refuse | refused | 0 | 230 ms | - |
| txt-accents | 1/1 | 6 | 111 ms | - |
| txt-compound | 2/2 | 3 | 138 ms | - |
| txt-checklist | 1/1 | 1 | 112 ms | - |
| txt-conditional | 1/2 | 1 | 194 ms | - |
| txt-calc | 1/1 | 1 | 129 ms | - |
| txt-refuse | refused | 0 | 127 ms | - |
| csv-row | 1/1 | 1 | 161 ms | - |
| csv-overdue | 4/4 | 3 | 139 ms | - |
| csv-total | 0/2 | 0 | 145 ms | - |
| csv-refuse | FAIL: 1 sent | 1 | 167 ms | - |
| html-focused | 1/1 | 1 | 126 ms | - |
| html-compare | 2/2 | 4 | 191 ms | - |
| html-modal-words | 1/1 | 6 | 142 ms | - |
| html-refuse | refused | 0 | 142 ms | - |
