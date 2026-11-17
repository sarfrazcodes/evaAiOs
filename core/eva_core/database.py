import sqlite3
import os
import logging

DB_PATH = os.path.join(os.path.dirname(__file__), 'eva.db')

def init_db():
    """Initializes the SQLite database foundation for Phase 1."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create a basic configuration table to establish DB functionality
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        # Insert a default value to prove it works
        cursor.execute('''
            INSERT OR IGNORE INTO system_config (key, value)
            VALUES ('db_version', '1.0')
        ''')

        # Phase 2C: Planner and Task State
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                intent TEXT,
                status TEXT NOT NULL,
                current_step INTEGER DEFAULT 0,
                total_steps INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                result TEXT,
                error TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_steps (
                step_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                description TEXT NOT NULL,
                dependencies TEXT,
                action TEXT,
                status TEXT NOT NULL,
                result TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks (task_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS confirmations (
                confirmation_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                arguments TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks (task_id) ON DELETE CASCADE,
                FOREIGN KEY (step_id) REFERENCES task_steps (step_id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_confirmations_task ON confirmations(task_id)
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conv_msg_conv_id ON conversation_messages(conversation_id)
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                privacy TEXT NOT NULL DEFAULT 'public',
                pinned INTEGER DEFAULT 0,
                source TEXT DEFAULT 'user',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_cat ON memories(category)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_pinned ON memories(pinned)
        ''')

        # Personal memory schema extensions
        try:
            cursor.execute("ALTER TABLE memories ADD COLUMN key TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE memories ADD COLUMN confirmed INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key)
        ''')
        
        try:
            cursor.execute("ALTER TABLE task_steps ADD COLUMN action TEXT")
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
        conn.close()
        logging.info(f"Database initialized at {DB_PATH}")

        # Seed verified owner profile and assistant identity
        try:
            from core.eva_core.memory.personal_memory import get_personal_memory_manager
            get_personal_memory_manager()
        except Exception as seed_err:
            logging.warning(f"Personal memory seed deferred: {seed_err}")

        return True
    except Exception as e:
        if conn is not None:
            conn.rollback()
            conn.close()
        logging.error(f"Failed to initialize database: {e}")
        return False


def database_health() -> dict:
    """Return non-sensitive database availability information for diagnostics."""
    try:
        with sqlite3.connect(DB_PATH, timeout=2) as conn:
            conn.execute("SELECT 1")
        return {"available": True}
    except sqlite3.Error as exc:
        logging.error("Database health check failed: %s", exc)
        return {"available": False, "error": "database_unavailable"}
