# Retrieval evaluation

39 answerable questions over the demo collection (+6 unanswerable ones for the relevance threshold).

| Mode | Recall@1 | Recall@5 | Recall@10 | MRR | Precision@5 | Avg latency |
|---|---|---|---|---|---|---|
| vector | 0.74 | 0.97 | 1.00 | 0.820 | 0.20 | 8 ms |
| keyword | 0.33 | 0.77 | 0.90 | 0.522 | 0.15 | 2 ms |
| hybrid | 0.67 | 0.97 | 1.00 | 0.785 | 0.19 | 10 ms |
| hybrid_rerank | 0.79 | 0.95 | 0.97 | 0.850 | 0.19 | 1054 ms |

## Relevance threshold (reranker top score)

- Answerable questions: min 0.6905, median 0.9960
- Unanswerable questions: max 0.1255, median 0.0016
- Current `MIN_RELEVANCE` = 0.01: would wrongly refuse 0/39 answerable and correctly refuse 4/6 unanswerable questions.

Recall@k: share of questions with a correct chunk in the top k. MRR: average of 1/rank of the first correct chunk. Precision@5: share of the top 5 that are correct.
