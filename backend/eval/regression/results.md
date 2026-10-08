# Regression benchmark

Fixtures and questions from the 8 October 2026 regression report (`eval/regression/cases.jsonl`).

| Metric | Result |
|---|---|
| Ingestion (valid accepted, invalid rejected, titles) | 10/10 |
| Facet coverage (parts of a question with a supporting passage) | 74/74 (100%) |
| Questions with every facet covered | 48/48 |
| Compound questions fully covered | 20/20 |
| Unanswerable questions stopped before the LLM (the rest must be refused by it) | 3/10 |
| Median retrieval latency | 1632 ms |
| Answers passing every check | 57/58 graded |

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
| pdf-allocation | 1/1 | 2 | 1035 ms | pass |
| pdf-percent | 1/1 | 2 | 950 ms | missing fact '30%' |
| pdf-cross-page | 2/2 | 2 | 1722 ms | pass |
| pdf-refuse | FAIL: 2 sent | 2 | 429 ms | pass |
| docx-table | 1/1 | 1 | 461 ms | pass |
| docx-header | 1/1 | 4 | 1067 ms | pass |
| docx-footer | 1/1 | 1 | 730 ms | pass |
| docx-list | 1/1 | 1 | 700 ms | pass |
| docx-conditional | 2/2 | 2 | 1656 ms | pass |
| docx-reentry | 1/1 | 1 | 859 ms | pass |
| docx-refuse | FAIL: 6 sent | 6 | 250 ms | pass |
| md-table | 1/1 | 6 | 262 ms | pass |
| md-code | 1/1 | 1 | 684 ms | pass |
| md-compound | 4/4 | 4 | 1470 ms | pass |
| md-isolated | 1/1 | 1 | 759 ms | pass |
| md-calc | 1/1 | 2 | 1012 ms | pass |
| md-refuse | FAIL: 6 sent | 6 | 757 ms | pass |
| txt-accents | 1/1 | 6 | 355 ms | pass |
| txt-compound | 2/2 | 6 | 660 ms | pass |
| txt-checklist | 1/1 | 2 | 978 ms | pass |
| txt-conditional | 2/2 | 3 | 1221 ms | pass |
| txt-calc | 1/1 | 1 | 784 ms | pass |
| txt-refuse | refused | 0 | 451 ms | pass |
| html-focused | 1/1 | 1 | 811 ms | pass |
| html-compare | 2/2 | 4 | 3791 ms | pass |
| html-modal-words | 1/1 | 6 | 1119 ms | pass |
| html-refuse | refused | 0 | 984 ms | pass |
| live-pdf-1 | 2/2 | 3 | 1967 ms | pass |
| live-pdf-2 | 1/1 | 1 | 1123 ms | pass |
| live-pdf-3 | 2/2 | 1 | 4009 ms | pass |
| live-pdf-4 | 2/2 | 1 | 2000 ms | pass |
| live-pdf-5 | FAIL: 2 sent | 2 | 2796 ms | pass |
| live-docx-1 | 2/2 | 7 | 5912 ms | pass |
| live-docx-2 | 2/2 | 2 | 7249 ms | pass |
| live-docx-3 | 1/1 | 1 | 4409 ms | pass |
| live-docx-4 | 1/1 | 2 | 1993 ms | pass |
| live-docx-5 | 2/2 | 2 | 1922 ms | pass |
| live-docx-6 | 2/2 | 3 | 4342 ms | pass |
| live-docx-7 | refused | 0 | 3196 ms | pass |
| live-md-1 | 1/1 | 2 | 1593 ms | pass |
| live-md-2 | 1/1 | 1 | 1828 ms | pass |
| live-md-3 | 2/2 | 1 | 1943 ms | pass |
| live-md-4 | 3/3 | 4 | 1964 ms | pass |
| live-md-5 | 1/1 | 2 | 1393 ms | pass |
| live-md-6 | FAIL: 3 sent | 3 | 4946 ms | pass |
| live-txt-1 | 1/1 | 5 | 1925 ms | pass |
| live-txt-2 | 2/2 | 2 | 4832 ms | pass |
| live-txt-3 | 1/1 | 3 | 1523 ms | pass |
| live-txt-4 | 1/1 | 1 | 1632 ms | pass |
| live-txt-5 | 2/2 | 7 | 2172 ms | pass |
| live-txt-6 | 1/1 | 3 | 4323 ms | pass |
| live-txt-7 | 1/1 | 3 | 2072 ms | pass |
| live-txt-8 | FAIL: 4 sent | 4 | 1398 ms | pass |
| live-csv-1 | 1/1 | 2 | 10407 ms | pass |
| live-csv-2 | 4/4 | 6 | 2754 ms | pass |
| live-csv-3 | 2/2 | 5 | 5185 ms | pass |
| live-csv-4 | 3/3 | 5 | 4204 ms | pass |
| live-csv-5 | FAIL: 4 sent | 4 | 3224 ms | pass |
