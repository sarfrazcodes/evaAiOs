import sqlite3
import os
import logging

DB_PATH = os.path.join(os.path.dirname(__file__), 'eva.db')

def init_db():
    """Initializes the SQLite database foundation for Phase 1."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
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
        
        try:
            cursor.execute("ALTER TABLE task_steps ADD COLUMN action TEXT")
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
        conn.close()
        logging.info(f"Database initialized at {DB_PATH}")
        return True
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}")
        return False
