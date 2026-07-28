CREATE TABLE IF NOT EXISTS nodes (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    node_type TEXT NOT NULL,
    aliases TEXT[] NOT NULL DEFAULT '{}',
    description TEXT,
    source_chunk_ids UUID[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    path TEXT NOT NULL,
    name TEXT NOT NULL,
    chunks_count INTEGER NOT NULL DEFAULT 0,
    checksum TEXT UNIQUE NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    text TEXT NOT NULL,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    idx INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS nodes (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    node_type TEXT NOT NULL,
    aliases TEXT[] NOT NULL DEFAULT '{}',
    description TEXT,
    source_chunk_ids UUID[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS edges (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    source_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relation TEXT NOT NULL,
    source_chunk_id UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT clock_timestamp(),
    UNIQUE(source_id, target_id, relation, source_chunk_id)
);

CREATE TABLE IF NOT EXISTS evidence_paths (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    question TEXT NOT NULL,
    entry_nodes UUID[] NOT NULL DEFAULT '{}',
    visited_nodes UUID[] NOT NULL DEFAULT '{}',
    traversed_edges UUID[] NOT NULL DEFAULT '{}',
    source_chunks UUID[] NOT NULL DEFAULT '{}',
    answer TEXT,
    confidence REAL,
    created_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

CREATE INDEX idx_edges_source ON edges(source_id);
CREATE INDEX idx_edges_target ON edges(target_id);
CREATE INDEX idx_edges_relation ON edges(relation);
CREATE INDEX idx_chunks_doc ON chunks(document_id);
CREATE INDEX idx_evidence_question ON evidence_paths(question);
CREATE INDEX idx_nodes_type ON nodes(node_type);