# Regression benchmark

Fixtures and questions from the 8 October 2026 regression report (`eval/regression/cases.jsonl`).

| Metric | Result |
|---|---|
| Ingestion (valid accepted, invalid rejected, titles) | 4/7 |
| Facet coverage (parts of a question with a supporting passage) | 31/37 (84%) |
| Questions with every facet covered | 20/25 |
| Compound questions fully covered | 5/8 |
| Unanswerable questions stopped before the LLM | 4/6 |
| Median retrieval latency | 140 ms |

## Ingestion

| Case | Result | Detail |
|---|---|---|
| pdf-ingest | FAIL | title '(anonymous)', expected 'Aurora Quay Berth Allocation Plan 2026' |
| docx-ingest | FAIL | title 'sable ridge', expected 'Sable Ridge Tunnel Gas Safety Procedure' |
| md-ingest | pass | title 'Ember Canal Lock Operations Guide', 13 sections |
| txt-ingest | FAIL | title 'mont riviere', expected 'Mont Rivière Upper-Air Station' |
| csv-ingest | pass | title 'tidal grid', 10 sections |
| csv-reject | pass | rejected: 'tidal_grid_headerless.csv' has '48' as a column name. The first row looks like data: add a header row with a name for each column. |
| html-ingest | pass | title 'HT-NAMES: Reserved Names for Harbour Telemetry', 8 sections |

## Questions

| Case | Facets covered | Sources sent | Latency | Answer |
|---|---|---|---|---|
| pdf-allocation | 1/1 | 2 | 101 ms | - |
| pdf-percent | 1/1 | 2 | 132 ms | - |
| pdf-cross-page | 2/2 | 2 | 109 ms | - |
| pdf-refuse | refused | 0 | 83 ms | - |
| docx-table | 1/1 | 1 | 131 ms | - |
| docx-header | 0/1 | 0 | 131 ms | - |
| docx-footer | 0/1 | 0 | 167 ms | - |
| docx-list | 1/1 | 1 | 122 ms | - |
| docx-conditional | 2/2 | 1 | 141 ms | - |
| docx-reentry | 1/1 | 1 | 125 ms | - |
| docx-refuse | FAIL: 3 sent | 3 | 129 ms | - |
| md-table | 1/1 | 6 | 270 ms | - |
| md-code | 1/1 | 1 | 248 ms | - |
| md-compound | 3/4 | 3 | 292 ms | - |
| md-isolated | 1/1 | 1 | 226 ms | - |
| md-calc | 1/1 | 2 | 233 ms | - |
| md-refuse | refused | 0 | 200 ms | - |
| txt-accents | 1/1 | 3 | 122 ms | - |
| txt-compound | 2/2 | 3 | 145 ms | - |
| txt-checklist | 1/1 | 1 | 123 ms | - |
| txt-conditional | 1/2 | 1 | 169 ms | - |
| txt-calc | 1/1 | 1 | 165 ms | - |
| txt-refuse | refused | 0 | 140 ms | - |
| csv-row | 1/1 | 1 | 155 ms | - |
| csv-overdue | 4/4 | 3 | 131 ms | - |
| csv-total | 0/2 | 0 | 129 ms | - |
| csv-refuse | FAIL: 1 sent | 1 | 154 ms | - |
| html-focused | 1/1 | 1 | 119 ms | - |
| html-compare | 2/2 | 4 | 150 ms | - |
| html-modal-words | 1/1 | 6 | 157 ms | - |
| html-refuse | refused | 0 | 137 ms | - |
