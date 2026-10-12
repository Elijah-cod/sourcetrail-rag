# Regression benchmark

Fixtures and questions from the 8 October 2026 regression report (`eval/regression/cases.jsonl`).

| Metric | Result |
|---|---|
| Ingestion (valid accepted, invalid rejected, titles) | 10/10 |
| Facet coverage (parts of a question with a supporting passage) | 77/77 (100%) |
| Questions with every facet covered | 51/51 |
| Compound questions fully covered | 20/20 |
| Unanswerable questions stopped before the LLM (the rest must be refused by it) | 3/10 |
| Answerable questions with a part reported as uncovered | 1/51 |
| Median retrieval latency | 763 ms |

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
| pdf-allocation | 1/1 | 2 | 382 ms | - |
| pdf-percent | 1/1 | 2 | 326 ms | - |
| pdf-cross-page | 2/2 | 2 | 1046 ms | - |
| pdf-refuse | reached the LLM (2 sent) | 2 | 214 ms | - |
| docx-table | 1/1 | 1 | 148 ms | - |
| docx-header | 1/1 | 4 | 427 ms | - |
| docx-footer | 1/1 | 1 | 298 ms | - |
| docx-list | 1/1 | 1 | 248 ms | - |
| docx-conditional | 2/2 | 2 | 911 ms | - |
| docx-reentry | 1/1 | 1 | 330 ms | - |
| docx-refuse | reached the LLM (6 sent) | 6 | 169 ms | - |
| md-table | 1/1 | 6 | 205 ms | - |
| md-code | 1/1 | 1 | 207 ms | - |
| md-compound | 4/4 | 4 | 861 ms | - |
| md-isolated | 1/1 | 1 | 205 ms | - |
| md-calc | 1/1 | 2 | 200 ms | - |
| md-refuse | reached the LLM (4 sent) | 4 | 218 ms | - |
| txt-accents | 1/1 | 6 | 217 ms | - |
| txt-compound | 2/2 | 6 | 444 ms | - |
| txt-checklist | 1/1 | 2 | 282 ms | - |
| txt-conditional | 2/2 | 3 | 801 ms | - |
| txt-calc | 1/1 | 1 | 221 ms | - |
| txt-refuse | refused | 0 | 234 ms | - |
| html-focused | 1/1 | 1 | 327 ms | - |
| html-compare | 2/2 | 4 | 809 ms | - |
| html-modal-words | 1/1 | 6 | 565 ms | - |
| html-refuse | refused | 0 | 303 ms | - |
| live-pdf-1 | 2/2 | 3 | 1189 ms | - |
| live-pdf-2 | 1/1 | 1 | 323 ms | - |
| live-pdf-3 | 2/2 (uncovered: repetition interval are required) | 1 | 2166 ms | - |
| live-pdf-4 | 2/2 | 1 | 1274 ms | - |
| live-pdf-5 | reached the LLM (2 sent) | 2 | 1716 ms | - |
| live-docx-1 | 2/2 | 7 | 2232 ms | - |
| live-docx-2 | 2/2 | 2 | 2872 ms | - |
| live-docx-3 | 1/1 | 1 | 905 ms | - |
| live-docx-4 | 1/1 | 2 | 889 ms | - |
| live-docx-5 | 2/2 | 2 | 765 ms | - |
| live-docx-6 | 2/2 | 4 | 937 ms | - |
| live-docx-7 | refused | 0 | 1208 ms | - |
| live-md-1 | 1/1 | 2 | 763 ms | - |
| live-md-2 | 1/1 | 1 | 988 ms | - |
| live-md-3 | 2/2 | 1 | 856 ms | - |
| live-md-4 | 3/3 | 4 | 911 ms | - |
| live-md-5 | 1/1 | 2 | 518 ms | - |
| live-md-6 | reached the LLM (3 sent) | 3 | 1860 ms | - |
| live-txt-1 | 1/1 | 5 | 869 ms | - |
| live-txt-2 | 2/2 | 2 | 2083 ms | - |
| live-txt-3 | 1/1 | 3 | 504 ms | - |
| live-txt-4 | 1/1 | 1 | 802 ms | - |
| live-txt-5 | 2/2 | 7 | 969 ms | - |
| live-txt-6 | 1/1 | 3 | 723 ms | - |
| live-txt-7 | 1/1 | 3 | 1168 ms | - |
| live-txt-8 | reached the LLM (4 sent) | 4 | 762 ms | - |
| live-csv-1 | 1/1 | 2 | 577 ms | - |
| live-csv-2 | 4/4 | 6 | 865 ms | - |
| live-csv-3 | 2/2 | 5 | 2565 ms | - |
| live-csv-4 | 3/3 | 5 | 1581 ms | - |
| live-csv-5 | reached the LLM (4 sent) | 4 | 1259 ms | - |
| live-csv-6 | 1/1 | 5 | 274 ms | - |
| live-csv-7 | 1/1 | 14 | 1236 ms | - |
| live-csv-8 | 1/1 | 5 | 757 ms | - |
