import os
import re
import sqlite3
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import core.eva_core.database as db_module

logger = logging.getLogger(__name__)

INITIAL_OWNER_PROFILE = {
    "nickname": "Saif",
    "full_name": "Mohd Sarfraz Saifi",
    "preferred_name": "Sarfraz",
    "call_name": "Saif",
    "occupation": "BTech Computer Science Engineering student",
    "creator_of_eva": True,
}

INITIAL_ASSISTANT_IDENTITY = {
    "name": "EVA",
    "creator_name": "Sarfraz",
    "creator_full_name": "Mohd Sarfraz Saifi",
}

MEMORY_CATEGORIES = [
    "Owner Profile",
    "Personal Preferences",
    "Education",
    "Projects",
    "Skills",
    "Important Information",
    "Private Memory",
    "Public Memory",
]


class PersonalMemoryManager:
    """Manages persistent personal identity and structured long-term memory in SQLite."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PersonalMemoryManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        if getattr(self, "_initialized", False):
            return
        self.db_path = db_path or db_module.DB_PATH
        self._ensure_schema_and_seed()
        self._initialized = True

    def _get_connection(self):
        path = self.db_path if (self.db_path and self.db_path != db_module.DB_PATH) else db_module.DB_PATH
        return sqlite3.connect(path, timeout=10)

    def _ensure_schema_and_seed(self):
        """Ensures the memories table has key and confirmed columns and seeds verified initial identity."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Ensure memories table exists
                cursor.execute("""
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
                """)

                # Add key and confirmed columns if missing
                cursor.execute("PRAGMA table_info(memories)")
                columns = [col[1] for col in cursor.fetchall()]
                if "key" not in columns:
                    try:
                        cursor.execute("ALTER TABLE memories ADD COLUMN key TEXT")
                    except sqlite3.OperationalError:
                        pass
                if "confirmed" not in columns:
                    try:
                        cursor.execute("ALTER TABLE memories ADD COLUMN confirmed INTEGER DEFAULT 1")
                    except sqlite3.OperationalError:
                        pass

                cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_cat ON memories(category)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_pinned ON memories(pinned)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key)")
                conn.commit()

                # Seed verified owner and assistant profile
                self._seed_initial_profile(cursor, conn)
        except Exception as e:
            logger.error(f"Error ensuring personal memory schema: {e}")

    def _seed_initial_profile(self, cursor, conn):
        """Seeds initial verified owner facts into SQLite without duplicating."""
        now = datetime.now(timezone.utc).isoformat()
        seeds = [
            (
                "mem_owner_nickname",
                "Nickname",
                "Saif",
                "Owner Profile",
                "private",
                1,
                "verified_owner",
                "nickname",
                1,
            ),
            (
                "mem_owner_fullname",
                "Full Name",
                "Mohd Sarfraz Saifi",
                "Owner Profile",
                "private",
                1,
                "verified_owner",
                "full_name",
                1,
            ),
            (
                "mem_owner_preferred",
                "Preferred Name",
                "Sarfraz",
                "Owner Profile",
                "private",
                1,
                "verified_owner",
                "preferred_name",
                1,
            ),
            (
                "mem_owner_callname",
                "Addressing Name",
                "Saif",
                "Owner Profile",
                "private",
                1,
                "verified_owner",
                "call_name",
                1,
            ),
            (
                "mem_owner_occupation",
                "Occupation",
                "BTech Computer Science Engineering student",
                "Education",
                "private",
                1,
                "verified_owner",
                "occupation",
                1,
            ),
            (
                "mem_owner_creator",
                "Creator of EVA",
                "true",
                "Owner Profile",
                "private",
                1,
                "verified_owner",
                "creator_of_eva",
                1,
            ),
            (
                "mem_asst_name",
                "Assistant Name",
                "EVA",
                "Public Memory",
                "public",
                1,
                "system_seed",
                "assistant_name",
                1,
            ),
            (
                "mem_asst_creator",
                "Creator Name",
                "Sarfraz",
                "Public Memory",
                "public",
                1,
                "system_seed",
                "creator_name",
                1,
            ),
            (
                "mem_asst_creator_fullname",
                "Creator Full Name",
                "Mohd Sarfraz Saifi",
                "Public Memory",
                "public",
                1,
                "system_seed",
                "creator_full_name",
                1,
            ),
        ]

        for mem_id, title, content, cat, priv, pinned, src, key, conf in seeds:
            cursor.execute("SELECT memory_id, content FROM memories WHERE key = ?", (key,))
            existing = cursor.fetchone()
            if not existing:
                cursor.execute(
                    """
                    INSERT INTO memories (memory_id, title, content, category, privacy, pinned, source, created_at, updated_at, key, confirmed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (mem_id, title, content, cat, priv, pinned, src, now, now, key, conf),
                )
        conn.commit()

    def get_owner_profile(self) -> Dict[str, Any]:
        """Returns structured dictionary of the owner's persistent profile from SQLite."""
        profile = {
            "nickname": "Saif",
            "full_name": "Mohd Sarfraz Saifi",
            "preferred_name": "Sarfraz",
            "call_name": "Saif",
            "occupation": "BTech Computer Science Engineering student",
            "creator_of_eva": True,
        }
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT key, content FROM memories WHERE (key IS NOT NULL AND key LIKE 'owner%') OR key IN ('nickname', 'full_name', 'preferred_name', 'call_name', 'occupation', 'creator_of_eva')"
                )
                rows = cursor.fetchall()
                for key, content in rows:
                    if key in profile:
                        if key == "creator_of_eva":
                            profile[key] = str(content).strip().lower() in ("true", "1", "yes")
                        else:
                            profile[key] = str(content).strip()
        except Exception as e:
            logger.error(f"Error reading owner profile from DB: {e}")
        return profile

    def get_assistant_identity(self) -> Dict[str, Any]:
        """Returns structured dictionary of assistant identity from SQLite."""
        asst = {
            "name": "EVA",
            "creator_name": "Sarfraz",
            "creator_full_name": "Mohd Sarfraz Saifi",
        }
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, content FROM memories WHERE key IN ('assistant_name', 'creator_name', 'creator_full_name')")
                rows = cursor.fetchall()
                for key, content in rows:
                    if key == "assistant_name":
                        asst["name"] = str(content).strip()
                    elif key == "creator_name":
                        asst["creator_name"] = str(content).strip()
                    elif key == "creator_full_name":
                        asst["creator_full_name"] = str(content).strip()
        except Exception as e:
            logger.error(f"Error reading assistant identity from DB: {e}")
        return asst

    def get_identity_fast_response(self, text: str) -> Optional[str]:
        """
        Deterministic fast-path retrieval for critical personal identity questions.
        Resolves directly from verified SQLite records without risking LLM hallucination.
        """
        raw = text.lower().strip()
        # Strip trailing punctuation
        normalized = re.sub(r"[?!.,;]+$", "", raw).strip()
        # Collapse multiple spaces
        normalized = re.sub(r"\s+", " ", normalized)

        owner = self.get_owner_profile()
        asst = self.get_assistant_identity()

        nickname = owner.get("nickname", "Saif")
        full_name = owner.get("full_name", "Mohd Sarfraz Saifi")
        preferred_name = owner.get("preferred_name", "Sarfraz")
        call_name = owner.get("call_name", "Saif")
        occupation = owner.get("occupation", "BTech Computer Science Engineering student")
        creator_name = asst.get("creator_name", "Sarfraz")
        creator_full_name = asst.get("creator_full_name", "Mohd Sarfraz Saifi")

        # 1. "Who am I?"
        if normalized in {
            "who am i",
            "who am i really",
            "tell me who i am",
            "do you know who i am",
            "who is this",
        }:
            return f"You are {nickname}, a {occupation}."

        # 2. "What is my name?"
        if normalized in {
            "what is my name",
            "whats my name",
            "what's my name",
            "tell me my name",
            "do you know my name",
        }:
            return f"Your name is {full_name}, and you prefer to be called {call_name}."

        # 2b. "What is my nickname?"
        if normalized in {
            "what is my nickname",
            "whats my nickname",
            "what's my nickname",
            "tell me my nickname",
        }:
            return f"Your nickname is {nickname}."

        # 2c. "What is my full name?"
        if normalized in {
            "what is my full name",
            "whats my full name",
            "what's my full name",
            "tell me my full name",
        }:
            return f"Your full name is {full_name}."

        # 3. "Who created you?"
        if normalized in {
            "who created you",
            "who made you",
            "who is your creator",
            "who built you",
            "who designed you",
            "who programmed you",
        }:
            return f"I was created by {creator_name}."

        # 4. "What is your creator's full name?"
        if normalized in {
            "what is your creators full name",
            "what is your creator's full name",
            "whats your creators full name",
            "what's your creator's full name",
            "what is the full name of your creator",
            "who is your creator full name",
        }:
            return f"My creator's full name is {creator_full_name}."

        # 5. "What do I do?"
        if normalized in {
            "what do i do",
            "what is my occupation",
            "what is my job",
            "what do i study",
            "what is my profession",
            "what's my occupation",
            "what's my job",
        }:
            return f"You are a {occupation}."

        # 6. "Do you remember who created you?"
        if normalized in {
            "do you remember who created you",
            "do you remember who made you",
            "do you know who created you",
            "remember who created you",
        }:
            return f"Yes. I was created by {creator_name}."

        # 7. "What do you know about me?"
        if normalized in {
            "what do you know about me",
            "tell me what you know about me",
            "what is in my profile",
            "what information do you have about me",
            "show my info",
        }:
            summary = (
                f"Here is what I know about you: Your name is {full_name}, and you prefer to be called {call_name}. "
                f"You are a {occupation}, and you are the creator of EVA."
            )
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT title, content, category FROM memories 
                        WHERE key NOT IN ('nickname', 'full_name', 'preferred_name', 'call_name', 'occupation', 'creator_of_eva', 'assistant_name', 'creator_name', 'creator_full_name')
                           OR key IS NULL
                        ORDER BY pinned DESC, updated_at DESC
                        LIMIT 5
                        """
                    )
                    extras = cursor.fetchall()
                    if extras:
                        extra_summary = "; ".join(f"{r[0]}: {r[1]}" for r in extras)
                        summary += f" You also have saved memories: {extra_summary}."
            except Exception:
                pass
            return summary


        # NOTE: Greetings ("hello eva", "hi eva", etc.) are intentionally NOT handled here.
        # They are conversational and should flow through the normal conversation route.

        return None

    def get_all_memories(
        self,
        category: Optional[str] = None,
        privacy: Optional[str] = None,
        search: Optional[str] = None,
        sort_newest: bool = True,
    ) -> List[Dict[str, Any]]:
        """Retrieves memories with optional filtering and sorting."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT memory_id, title, content, category, privacy, pinned, source, created_at, updated_at, key, confirmed FROM memories WHERE 1=1"
                params = []

                if category and category != "All Memory":
                    if category == "Important Information":
                        query += " AND pinned = 1"
                    elif category == "Private Memory":
                        query += " AND privacy = 'private'"
                    elif category == "Public Memory":
                        query += " AND privacy = 'public'"
                    else:
                        query += " AND category = ?"
                        params.append(category)

                if privacy:
                    query += " AND privacy = ?"
                    params.append(privacy)

                if search:
                    query += " AND (title LIKE ? OR content LIKE ? OR key LIKE ?)"
                    term = f"%{search}%"
                    params.extend([term, term, term])

                order = "DESC" if sort_newest else "ASC"
                query += f" ORDER BY pinned DESC, updated_at {order}"

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [
                    {
                        "memory_id": r[0],
                        "title": r[1],
                        "content": r[2],
                        "category": r[3],
                        "privacy": r[4],
                        "pinned": bool(r[5]),
                        "source": r[6],
                        "created_at": r[7],
                        "updated_at": r[8],
                        "key": r[9],
                        "confirmed": bool(r[10]) if r[10] is not None else True,
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Error fetching memories: {e}")
            return []

    def get_structured_llm_context(self, include_private: bool = True) -> str:
        """
        Formats verified personal and assistant memories into structured context for the LLM.
        If include_private is False (e.g. for cloud models without authorization),
        private memory is strictly excluded.
        """
        owner = self.get_owner_profile()
        asst = self.get_assistant_identity()

        context_lines = [
            "### PERSISTENT SYSTEM & ASSISTANT IDENTITY:",
            f"- Assistant Name: {asst.get('name', 'EVA')}",
            f"- Creator: {asst.get('creator_name', 'Sarfraz')}",
            f"- Creator Full Name: {asst.get('creator_full_name', 'Mohd Sarfraz Saifi')}",
        ]

        if include_private:
            context_lines.extend([
                "\n### VERIFIED OWNER PROFILE (PRIVATE LOCAL MEMORY):",
                f"- Name: {owner.get('full_name', 'Mohd Sarfraz Saifi')}",
                f"- Preferred Name / Nickname: {owner.get('nickname', 'Saif')}",
                f"- Primary Calling Name: {owner.get('call_name', 'Saif')}",
                f"- Occupation & Education: {owner.get('occupation', 'BTech Computer Science Engineering student')}",
                f"- Creator of EVA: {'Yes' if owner.get('creator_of_eva') else 'No'}",
            ])

            # Fetch all user-defined memories from SQLite
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT title, content, category, pinned 
                        FROM memories 
                        WHERE key NOT IN ('nickname', 'full_name', 'preferred_name', 'call_name', 'occupation', 'creator_of_eva', 'assistant_name', 'creator_name', 'creator_full_name')
                           OR key IS NULL
                        ORDER BY pinned DESC, updated_at DESC
                        """
                    )
                    user_mems = cursor.fetchall()
                    if user_mems:
                        context_lines.append("\n### STORED USER MEMORIES & PREFERENCES (GROUND TRUTH):")
                        for title, content, category, pinned in user_mems:
                            pin_mark = "[PINNED] " if pinned else ""
                            context_lines.append(f"- {pin_mark}[{category}] {title}: {content}")
            except Exception as e:
                logger.error(f"Error fetching extended memories for context: {e}")
        else:
            context_lines.append("\n[Private owner profile withheld due to privacy policy]")
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT title, content, category 
                        FROM memories 
                        WHERE privacy = 'public' 
                          AND (key NOT IN ('assistant_name', 'creator_name', 'creator_full_name') OR key IS NULL)
                        ORDER BY pinned DESC, updated_at DESC
                        """
                    )
                    pub_mems = cursor.fetchall()
                    if pub_mems:
                        context_lines.append("\n### PUBLIC SYSTEM MEMORIES:")
                        for title, content, category in pub_mems:
                            context_lines.append(f"- [{category}] {title}: {content}")
            except Exception as e:
                logger.error(f"Error fetching public memories: {e}")

        return "\n".join(context_lines)


def get_personal_memory_manager() -> PersonalMemoryManager:
    return PersonalMemoryManager()
