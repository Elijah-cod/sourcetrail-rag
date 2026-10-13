# Retrieval evaluation

39 answerable questions over the demo collection (+6 unanswerable ones for the relevance threshold).

| Mode | Recall@1 | Recall@5 | Recall@10 | MRR | Precision@5 | Avg latency |
|---|---|---|---|---|---|---|
| vector | 0.79 | 0.97 | 1.00 | 0.854 | 0.20 | 10 ms |
| keyword | 0.31 | 0.72 | 0.85 | 0.488 | 0.14 | 3 ms |
| hybrid | 0.64 | 0.97 | 1.00 | 0.762 | 0.19 | 12 ms |
| hybrid_rerank | 0.79 | 0.97 | 0.97 | 0.852 | 0.20 | 410 ms |

## Relevance threshold (reranker top score)

- Answerable questions: min 0.6505, median 0.9973
- Unanswerable questions: max 0.1255, median 0.0016
- Current `MIN_RELEVANCE` = 0.3: would wrongly refuse 0/39 answerable and correctly refuse 6/6 unanswerable questions.

Recall@k: share of questions with a correct chunk in the top k. MRR: average of 1/rank of the first correct chunk. Precision@5: share of the top 5 that are correct.
