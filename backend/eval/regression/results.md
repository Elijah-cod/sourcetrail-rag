# Regression benchmark

Fixtures and questions from the 8 October 2026 regression report (`eval/regression/cases.jsonl`).

| Metric | Result |
|---|---|
| Ingestion (valid accepted, invalid rejected, titles) | 10/10 |
| Facet coverage (parts of a question with a supporting passage) | 95/95 (100%) |
| Questions with every facet covered | 55/55 |
| Compound questions fully covered | 24/24 |
| Unanswerable questions stopped before the LLM (the rest must be refused by it) | 3/10 |
| Answerable questions with a part reported as uncovered | 1/55 |
| Median retrieval latency | 727 ms |

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
| pdf-allocation | 1/1 | 2 | 325 ms | - |
| pdf-percent | 1/1 | 2 | 304 ms | - |
| pdf-cross-page | 2/2 | 2 | 886 ms | - |
| pdf-refuse | reached the LLM (2 sent) | 2 | 222 ms | - |
| docx-table | 1/1 | 1 | 166 ms | - |
| docx-header | 1/1 | 4 | 293 ms | - |
| docx-footer | 1/1 | 1 | 272 ms | - |
| docx-list | 1/1 | 1 | 214 ms | - |
| docx-conditional | 2/2 | 2 | 830 ms | - |
| docx-reentry | 1/1 | 1 | 260 ms | - |
| docx-refuse | reached the LLM (6 sent) | 6 | 159 ms | - |
| md-table | 1/1 | 6 | 166 ms | - |
| md-code | 1/1 | 1 | 181 ms | - |
| md-compound | 4/4 | 4 | 1062 ms | - |
| md-isolated | 1/1 | 1 | 228 ms | - |
| md-calc | 1/1 | 2 | 230 ms | - |
| md-refuse | reached the LLM (4 sent) | 4 | 230 ms | - |
| txt-accents | 1/1 | 6 | 185 ms | - |
| txt-compound | 2/2 | 6 | 430 ms | - |
| txt-checklist | 1/1 | 2 | 202 ms | - |
| txt-conditional | 2/2 | 3 | 607 ms | - |
| txt-calc | 1/1 | 1 | 212 ms | - |
| txt-refuse | refused | 0 | 179 ms | - |
| html-focused | 1/1 | 1 | 256 ms | - |
| html-compare | 2/2 | 4 | 734 ms | - |
| html-modal-words | 1/1 | 6 | 385 ms | - |
| html-refuse | refused | 0 | 328 ms | - |
| live-pdf-1 | 2/2 | 3 | 1348 ms | - |
| live-pdf-2 | 1/1 | 1 | 827 ms | - |
| live-pdf-3 | 2/2 (uncovered: repetition interval are required) | 1 | 1726 ms | - |
| live-pdf-4 | 2/2 | 1 | 1087 ms | - |
| live-pdf-5 | reached the LLM (2 sent) | 2 | 1433 ms | - |
| live-docx-1 | 2/2 | 7 | 1742 ms | - |
| live-docx-2 | 2/2 | 2 | 1973 ms | - |
| live-docx-3 | 1/1 | 1 | 647 ms | - |
| live-docx-4 | 1/1 | 2 | 852 ms | - |
| live-docx-5 | 2/2 | 2 | 736 ms | - |
| live-docx-6 | 2/2 | 4 | 1567 ms | - |
| live-docx-7 | refused | 0 | 1066 ms | - |
| live-md-1 | 1/1 | 2 | 733 ms | - |
| live-md-2 | 1/1 | 1 | 946 ms | - |
| live-md-3 | 2/2 | 1 | 850 ms | - |
| live-md-4 | 3/3 | 4 | 870 ms | - |
| live-md-5 | 1/1 | 2 | 590 ms | - |
| live-md-6 | reached the LLM (3 sent) | 3 | 1529 ms | - |
| live-txt-1 | 1/1 | 5 | 857 ms | - |
| live-txt-2 | 2/2 | 2 | 1981 ms | - |
| live-txt-3 | 1/1 | 3 | 394 ms | - |
| live-txt-4 | 1/1 | 1 | 727 ms | - |
| live-txt-5 | 2/2 | 7 | 867 ms | - |
| live-txt-6 | 1/1 | 3 | 623 ms | - |
| live-txt-7 | 1/1 | 3 | 1089 ms | - |
| live-txt-8 | reached the LLM (4 sent) | 4 | 592 ms | - |
| live-csv-1 | 1/1 | 2 | 461 ms | - |
| live-csv-2 | 4/4 | 6 | 933 ms | - |
| live-csv-3 | 2/2 | 5 | 1991 ms | - |
| live-csv-4 | 3/3 | 5 | 1391 ms | - |
| live-csv-5 | reached the LLM (4 sent) | 4 | 991 ms | - |
| live-csv-6 | 1/1 | 5 | 287 ms | - |
| live-csv-7 | 1/1 | 14 | 1155 ms | - |
| live-csv-8 | 1/1 | 5 | 706 ms | - |
| cross-2 | 2/2 | 4 | 517 ms | - |
| cross-4 | 4/4 | 5 | 947 ms | - |
| cross-6 | 6/6 | 7 | 1293 ms | - |
| live-six-documents | 6/6 | 7 | 1623 ms | - |
