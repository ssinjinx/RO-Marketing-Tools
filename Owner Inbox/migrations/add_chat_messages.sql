-- Add chat_messages table for dashboard↔orchestrator bridge
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL CHECK (direction IN ('in', 'out')),  -- 'in' = from dashboard, 'out' = from orchestrator
    content TEXT NOT NULL,
    sender TEXT DEFAULT 'user',  -- 'user' or 'orchestrator'
    read INTEGER DEFAULT 0,  -- 0 = unread, 1 = read
    created_at TEXT DEFAULT (datetime('now'))
);

-- Index for fast polling queries
CREATE INDEX IF NOT EXISTS idx_chat_unread ON chat_messages(direction, read, created_at);
