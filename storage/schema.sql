CREATE EXTENSION IF NOT EXISTS vector;

-- -----------------------------------------------------------------------------
-- Identity
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-create a profile row whenever a new auth user signs up.
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, display_name)
    VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'name', NEW.email));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- -----------------------------------------------------------------------------
-- Projects
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects (owner_id);
CREATE INDEX IF NOT EXISTS idx_projects_public ON projects (is_public) WHERE is_public = TRUE;


CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    -- same file can exist in two different projects; uniqueness is per-project
    UNIQUE (checksum, project_id)
);

CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    idx INTEGER DEFAULT 0,
    embedding VECTOR(384),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    node_type TEXT NOT NULL,
    aliases JSONB NOT NULL DEFAULT '[]',
    description TEXT,
    source_chunk_ids JSONB NOT NULL DEFAULT '[]',
    embedding VECTOR(384),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relation TEXT NOT NULL,
    source_chunk_id UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source_id, target_id, relation, source_chunk_id)
);

CREATE TABLE IF NOT EXISTS traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    entry_nodes JSONB DEFAULT '[]',
    visited_nodes JSONB DEFAULT '[]',
    traversed_edges JSONB DEFAULT '[]',
    source_chunks JSONB DEFAULT '[]',
    answer TEXT,
    confidence REAL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chat transcript, persisted only for signed-in users
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    steps JSONB DEFAULT '[]',
    confidence REAL,
    latency_ms REAL,
    trace_id UUID REFERENCES traces(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------------
-- Vector indexes
CREATE INDEX IF NOT EXISTS idx_nodes_embedding
ON nodes
USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding
ON chunks
USING hnsw (embedding vector_cosine_ops);

-- project_id scoping indexes — every load_* call in SupabaseGraphStore
-- filters on project_id first
CREATE INDEX IF NOT EXISTS idx_nodes_project ON nodes (project_id);
CREATE INDEX IF NOT EXISTS idx_edges_project ON edges (project_id);
CREATE INDEX IF NOT EXISTS idx_chunks_project ON chunks (project_id);
CREATE INDEX IF NOT EXISTS idx_documents_project ON documents (project_id);
CREATE INDEX IF NOT EXISTS idx_traces_project ON traces (project_id);


CREATE INDEX IF NOT EXISTS idx_chat_messages_project_user
ON chat_messages (project_id, user_id, created_at);

-- Standard performance indexes
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges (source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges (target_id);
CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges (relation);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_traces_question ON traces (question);
CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes (node_type);

-- -----------------------------------------------------------------------------
-- pgvector similarity search
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION match_nodes (
    query_embedding VECTOR(384),
    match_threshold FLOAT,
    match_count INT,
    filter_project_id UUID
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
        AND nodes.project_id = filter_project_id
        AND 1 - (nodes.embedding <=> query_embedding) > match_threshold
    ORDER BY nodes.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding VECTOR(384),
    match_threshold FLOAT,
    match_count INT,
    filter_project_id UUID
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
        AND chunks.project_id = filter_project_id
        AND 1 - (chunks.embedding <=> query_embedding) > match_threshold
    ORDER BY chunks.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Row Level Security
-- -----------------------------------------------------------------------------
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE traces ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- chat_messages gets its own policies rather than joining the shared loop
-- below: every other table is "accessible if the project is", but a chat
-- transcript is additionally private to the person who wrote it, even in
-- a public/shared project — you shouldn't see a stranger's questions.
DROP POLICY IF EXISTS "chat_messages: read own" ON chat_messages;
CREATE POLICY "chat_messages: read own" ON chat_messages
    FOR SELECT USING (
        user_id = auth.uid()
        AND project_id IN (SELECT id FROM projects WHERE is_public OR owner_id = auth.uid())
    );

DROP POLICY IF EXISTS "chat_messages: insert own" ON chat_messages;
CREATE POLICY "chat_messages: insert own" ON chat_messages
    FOR INSERT WITH CHECK (
        user_id = auth.uid()
        AND project_id IN (SELECT id FROM projects WHERE is_public OR owner_id = auth.uid())
    );

DROP POLICY IF EXISTS "chat_messages: delete own" ON chat_messages;
CREATE POLICY "chat_messages: delete own" ON chat_messages
    FOR DELETE USING (user_id = auth.uid());

DROP POLICY IF EXISTS "profiles are readable by anyone" ON profiles;
CREATE POLICY "profiles are readable by anyone" ON profiles
    FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS "projects: read own or public" ON projects;
CREATE POLICY "projects: read own or public" ON projects
    FOR SELECT USING (is_public OR owner_id = auth.uid());

DROP POLICY IF EXISTS "projects: insert own" ON projects;
CREATE POLICY "projects: insert own" ON projects
    FOR INSERT WITH CHECK (owner_id = auth.uid());

DROP POLICY IF EXISTS "projects: update own" ON projects;
CREATE POLICY "projects: update own" ON projects
    FOR UPDATE USING (owner_id = auth.uid());

DROP POLICY IF EXISTS "projects: delete own" ON projects;
CREATE POLICY "projects: delete own" ON projects
    FOR DELETE USING (owner_id = auth.uid());

-- Same read/write shape repeated for every graph table: readable if the
-- parent project is public, writable only if they own it.
-- Policies are dropped-then-created
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['documents', 'chunks', 'nodes', 'edges', 'traces']
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS "%1$s: read via project" ON %1$s;', t);
        EXECUTE format($f$
            CREATE POLICY "%1$s: read via project" ON %1$s
                FOR SELECT USING (
                    project_id IN (
                        SELECT id FROM projects WHERE is_public OR owner_id = auth.uid()
                    )
                );
        $f$, t);

        EXECUTE format('DROP POLICY IF EXISTS "%1$s: write via owned project" ON %1$s;', t);
        EXECUTE format($f$
            CREATE POLICY "%1$s: write via owned project" ON %1$s
                FOR INSERT WITH CHECK (
                    project_id IN (SELECT id FROM projects WHERE owner_id = auth.uid())
                );
        $f$, t);

        EXECUTE format('DROP POLICY IF EXISTS "%1$s: update via owned project" ON %1$s;', t);
        EXECUTE format($f$
            CREATE POLICY "%1$s: update via owned project" ON %1$s
                FOR UPDATE USING (
                    project_id IN (SELECT id FROM projects WHERE owner_id = auth.uid())
                );
        $f$, t);

        EXECUTE format('DROP POLICY IF EXISTS "%1$s: delete via owned project" ON %1$s;', t);
        EXECUTE format($f$
            CREATE POLICY "%1$s: delete via owned project" ON %1$s
                FOR DELETE USING (
                    project_id IN (SELECT id FROM projects WHERE owner_id = auth.uid())
                );
        $f$, t);
    END LOOP;
END $$;
