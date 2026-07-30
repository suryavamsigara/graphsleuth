CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path TEXT NOT NULL,
    name TEXT NOT NULL,
    checksum TEXT UNIQUE NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text TEXT NOT NULL,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    idx INTEGER DEFAULT 0,
    embedding VECTOR(384),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type TEXT NOT NULL,
    aliases JSONB NOT NULL DEFAULT '[]',
    description TEXT,
    source_chunk_ids JSONB NOT NULL DEFAULT '[]',
    embedding VECTOR(128),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relation TEXT NOT NULL,
    source_chunk_id UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source_id, target_id, relation, source_chunk_id)
);

CREATE TABLE IF NOT EXISTS evidence_paths (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    entry_nodes JSONB DEFAULT '[]',
    visited_nodes JSONB DEFAULT '[]',
    traversed_edges JSONB DEFAULT '[]',
    source_chunks JSONB DEFAULT '[]',
    answer TEXT,
    confidence REAL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vector indexes
CREATE INDEX IF NOT EXISTS idx_nodes_embedding
ON nodes
USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding
ON chunks
USING hnsw (embedding vector_cosine_ops);

-- Standard performance indexes
CREATE INDEX IF NOT EXISTS idx_edges_source
ON edges (source_id);

CREATE INDEX IF NOT EXISTS idx_edges_target
ON edges (target_id);

CREATE INDEX IF NOT EXISTS idx_edges_relation
ON edges (relation);

CREATE INDEX IF NOT EXISTS idx_chunks_doc
ON chunks (document_id);

CREATE INDEX IF NOT EXISTS idx_evidence_question
ON evidence_paths (question);

CREATE INDEX IF NOT EXISTS idx_nodes_type
ON nodes (node_type);

-- pgvector similarity search called via RPC
CREATE OR REPLACE FUNCTION match_nodes (
    query_embedding VECTOR(128),
    match_threshold FLOAT,
    match_count INT
)
RETURNS TABLE (
    id UUID,
    similarity FLOAT
)
AS $$
BEGIN
    RETURN QUERY
    SELECT
        nodes.id,
        1 - (nodes.embedding <=> query_embedding)::FLOAT AS similarity
    FROM nodes
    WHERE nodes.embedding IS NOT NULL
        AND 1 - (nodes.embedding <=> query_embedding) > match_threshold
    ORDER BY nodes.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding VECTOR(384),
    match_threshold FLOAT,
    match_count INT
)
RETURNS TABLE (
    id UUID,
    similarity FLOAT
)
AS $$
BEGIN
    RETURN QUERY
    SELECT
        chunks.id,
        1 - (chunks.embedding <=> query_embedding)::FLOAT AS similarity
    FROM chunks
    WHERE chunks.embedding IS NOT NULL
        AND 1 - (chunks.embedding <=> query_embedding) > match_threshold
    ORDER BY chunks.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql