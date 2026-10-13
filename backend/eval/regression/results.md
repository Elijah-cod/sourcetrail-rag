# Regression benchmark

Fixtures and questions from the 8 October 2026 regression report (`eval/regression/cases.jsonl`).

| Metric | Result |
|---|---|
| Ingestion (valid accepted, invalid rejected, titles) | 10/10 |
| Facet coverage (parts of a question with a supporting passage) | 89/89 (100%) |
| Questions with every facet covered | 54/54 |
| Compound questions fully covered | 23/23 |
| Unanswerable questions stopped before the LLM (the rest must be refused by it) | 3/10 |
| Answerable questions with a part reported as uncovered | 1/54 |
| Median retrieval latency | 698 ms |

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
| pdf-allocation | 1/1 | 2 | 273 ms | - |
| pdf-percent | 1/1 | 2 | 250 ms | - |
| pdf-cross-page | 2/2 | 2 | 840 ms | - |
| pdf-refuse | reached the LLM (2 sent) | 2 | 221 ms | - |
| docx-table | 1/1 | 1 | 186 ms | - |
| docx-header | 1/1 | 4 | 283 ms | - |
| docx-footer | 1/1 | 1 | 254 ms | - |
| docx-list | 1/1 | 1 | 220 ms | - |
| docx-conditional | 2/2 | 2 | 886 ms | - |
| docx-reentry | 1/1 | 1 | 264 ms | - |
| docx-refuse | reached the LLM (6 sent) | 6 | 175 ms | - |
| md-table | 1/1 | 6 | 261 ms | - |
| md-code | 1/1 | 1 | 239 ms | - |
| md-compound | 4/4 | 4 | 989 ms | - |
| md-isolated | 1/1 | 1 | 209 ms | - |
| md-calc | 1/1 | 2 | 201 ms | - |
| md-refuse | reached the LLM (4 sent) | 4 | 230 ms | - |
| txt-accents | 1/1 | 6 | 183 ms | - |
| txt-compound | 2/2 | 6 | 430 ms | - |
| txt-checklist | 1/1 | 2 | 259 ms | - |
| txt-conditional | 2/2 | 3 | 698 ms | - |
| txt-calc | 1/1 | 1 | 295 ms | - |
| txt-refuse | refused | 0 | 218 ms | - |
| html-focused | 1/1 | 1 | 247 ms | - |
| html-compare | 2/2 | 4 | 801 ms | - |
| html-modal-words | 1/1 | 6 | 416 ms | - |
| html-refuse | refused | 0 | 280 ms | - |
| live-pdf-1 | 2/2 | 3 | 1330 ms | - |
| live-pdf-2 | 1/1 | 1 | 341 ms | - |
| live-pdf-3 | 2/2 (uncovered: repetition interval are required) | 1 | 1606 ms | - |
| live-pdf-4 | 2/2 | 1 | 1097 ms | - |
| live-pdf-5 | reached the LLM (2 sent) | 2 | 1260 ms | - |
| live-docx-1 | 2/2 | 7 | 1596 ms | - |
| live-docx-2 | 2/2 | 2 | 1973 ms | - |
| live-docx-3 | 1/1 | 1 | 694 ms | - |
| live-docx-4 | 1/1 | 2 | 962 ms | - |
| live-docx-5 | 2/2 | 2 | 726 ms | - |
| live-docx-6 | 2/2 | 4 | 1487 ms | - |
| live-docx-7 | refused | 0 | 933 ms | - |
| live-md-1 | 1/1 | 2 | 816 ms | - |
| live-md-2 | 1/1 | 1 | 786 ms | - |
| live-md-3 | 2/2 | 1 | 683 ms | - |
| live-md-4 | 3/3 | 4 | 830 ms | - |
| live-md-5 | 1/1 | 2 | 581 ms | - |
| live-md-6 | reached the LLM (3 sent) | 3 | 1633 ms | - |
| live-txt-1 | 1/1 | 5 | 964 ms | - |
| live-txt-2 | 2/2 | 2 | 1699 ms | - |
| live-txt-3 | 1/1 | 3 | 449 ms | - |
| live-txt-4 | 1/1 | 1 | 712 ms | - |
| live-txt-5 | 2/2 | 7 | 1163 ms | - |
| live-txt-6 | 1/1 | 3 | 694 ms | - |
| live-txt-7 | 1/1 | 3 | 1017 ms | - |
| live-txt-8 | reached the LLM (4 sent) | 4 | 618 ms | - |
| live-csv-1 | 1/1 | 2 | 524 ms | - |
| live-csv-2 | 4/4 | 6 | 707 ms | - |
| live-csv-3 | 2/2 | 5 | 1938 ms | - |
| live-csv-4 | 3/3 | 5 | 1382 ms | - |
| live-csv-5 | reached the LLM (4 sent) | 4 | 1228 ms | - |
| live-csv-6 | 1/1 | 5 | 275 ms | - |
| live-csv-7 | 1/1 | 14 | 1119 ms | - |
| live-csv-8 | 1/1 | 5 | 717 ms | - |
| cross-2 | 2/2 | 4 | 470 ms | - |
| cross-4 | 4/4 | 5 | 983 ms | - |
| cross-6 | 6/6 | 7 | 1200 ms | - |
