-- 002_chunk_ids_per_document.sql
-- Fix: chunk IDs like "report-pdf:c000" are only unique *within a document*.
-- Two visitors can both upload "report.pdf", so a global primary key on chunks.id
-- would make the second upload fail. The key becomes (document_id, id) instead.

ALTER TABLE chunks DROP CONSTRAINT chunks_pkey;
ALTER TABLE chunks ADD PRIMARY KEY (document_id, id);
