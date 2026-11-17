import sqlite3
import json
import logging
import uuid
from datetime import timedelta
from typing import Optional, List
from datetime import datetime
from core.eva_core.protocol import TaskModel, TaskStatus, TaskStep, utc_now
from core.eva_core.database import DB_PATH, init_db

class TaskStateManager:
    def __init__(self):
        if not init_db():
            raise RuntimeError("Task database initialization failed.")

    def _get_connection(self):
        connection = sqlite3.connect(DB_PATH, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_task(self, request_id: str, intent: str) -> TaskModel:
        task = TaskModel(request_id=request_id, intent=intent, status=TaskStatus.PLANNING)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tasks (task_id, request_id, intent, status, current_step, total_steps, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (task.task_id, task.request_id, task.intent, task.status, task.current_step, task.total_steps, task.created_at.isoformat(), task.updated_at.isoformat()))
            conn.commit()
        return task

    def get_task(self, task_id: str) -> Optional[TaskModel]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT task_id, request_id, intent, status, current_step, total_steps, created_at, updated_at, result, error '
                'FROM tasks WHERE task_id = ?',
                (task_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            task = TaskModel(
                task_id=row[0],
                request_id=row[1],
                intent=row[2],
                status=TaskStatus(row[3]),
                current_step=row[4],
                total_steps=row[5],
                created_at=datetime.fromisoformat(row[6]),
                updated_at=datetime.fromisoformat(row[7]),
                result=json.loads(row[8]) if row[8] else None,
                error=json.loads(row[9]) if row[9] else None
            )

            # Use explicit column list to handle schema differences across DB versions.
            # 'action' column may be at position 5 (new DB) or added via ALTER TABLE (old DB).
            # We fetch it by name using a subquery or cursor.description approach.
            cursor.execute(
                'SELECT step_id, task_id, sequence, description, dependencies, '
                'action, status, result, error, created_at, updated_at '
                'FROM task_steps WHERE task_id = ? ORDER BY sequence ASC',
                (task_id,)
            )
            step_rows = cursor.fetchall()
            for s_row in step_rows:
                step = TaskStep(
                    step_id=s_row[0],
                    task_id=s_row[1],
                    sequence=s_row[2],
                    description=s_row[3],
                    dependencies=json.loads(s_row[4]) if s_row[4] else [],
                    action=json.loads(s_row[5]) if s_row[5] else None,
                    status=s_row[6],
                    result=json.loads(s_row[7]) if s_row[7] else None,
                    error=json.loads(s_row[8]) if s_row[8] else None,
                    created_at=datetime.fromisoformat(s_row[9]),
                    updated_at=datetime.fromisoformat(s_row[10])
                )
                task.steps.append(step)
            return task

    def list_tasks(self, limit: int = 50) -> List[TaskModel]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT task_id FROM tasks ORDER BY updated_at DESC LIMIT ?", (limit,))
            task_ids = [row[0] for row in cursor.fetchall()]
        return [task for task_id in task_ids if (task := self.get_task(task_id)) is not None]

    def save_plan(self, task_id: str, steps: List[TaskStep]) -> TaskModel:
        task = self.get_task(task_id)
        if not task:
            raise ValueError("Task not found")

        step_ids = {step.step_id for step in steps}
        if len(step_ids) != len(steps):
            raise ValueError("Plan contains duplicate step IDs.")
        for step in steps:
            if step.task_id != task_id:
                raise ValueError("Plan step belongs to a different task.")
            missing = set(step.dependencies) - step_ids
            if missing:
                raise ValueError(
                    f"Step {step.sequence} references missing dependencies: {sorted(missing)}"
                )
            if step.step_id in step.dependencies:
                raise ValueError(f"Step {step.sequence} cannot depend on itself.")
        
        now = utc_now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for step in steps:
                cursor.execute('''
                    INSERT INTO task_steps (step_id, task_id, sequence, description, dependencies, action, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (step.step_id, step.task_id, step.sequence, step.description, json.dumps(step.dependencies), json.dumps(step.action.model_dump()) if step.action else None, step.status, step.created_at.isoformat(), step.updated_at.isoformat()))
            
            total_steps = len(steps)
            cursor.execute('''
                UPDATE tasks SET total_steps = ?, updated_at = ? WHERE task_id = ?
            ''', (total_steps, now, task_id))
            conn.commit()
            
        return self.get_task(task_id)

    def claim_execution(self, task_id: str) -> bool:
        """Atomically claim a planned task for one executor."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                "UPDATE tasks SET status = ?, updated_at = ? "
                "WHERE task_id = ? AND status IN (?, ?)",
                (
                    TaskStatus.RUNNING,
                    utc_now().isoformat(),
                    task_id,
                    TaskStatus.PLANNED,
                    TaskStatus.READY,
                ),
            )
            claimed = cursor.rowcount == 1
            conn.commit()
            return claimed

    def create_or_get_confirmation(self, task_id: str, step_id: str, tool_name: str, arguments: dict, ttl_seconds: int = 60) -> dict:
        now = utc_now()
        expires_at = now + timedelta(seconds=ttl_seconds)
        arguments_json = json.dumps(arguments, sort_keys=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT confirmation_id, task_id, step_id, tool_name, arguments, status, created_at, expires_at "
                "FROM confirmations WHERE task_id = ? AND step_id = ? AND status = 'pending'",
                (task_id, step_id),
            )
            existing = cursor.fetchone()
            if existing:
                if datetime.fromisoformat(existing[7]) > now and existing[3] == tool_name and existing[4] == arguments_json:
                    return self._confirmation_dict(existing)
                cursor.execute(
                    "UPDATE confirmations SET status = 'expired', updated_at = ? WHERE confirmation_id = ?",
                    (now.isoformat(), existing[0]),
                )
            confirmation_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO confirmations "
                "(confirmation_id, task_id, step_id, tool_name, arguments, status, created_at, expires_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)",
                (confirmation_id, task_id, step_id, tool_name, arguments_json, now.isoformat(), expires_at.isoformat(), now.isoformat()),
            )
            conn.commit()
        return self.get_confirmation(confirmation_id)

    @staticmethod
    def _confirmation_dict(row):
        return {
            "confirmation_id": row[0],
            "task_id": row[1],
            "step_id": row[2],
            "tool_name": row[3],
            "arguments": json.loads(row[4]),
            "status": row[5],
            "created_at": row[6],
            "expires_at": row[7],
        }

    def get_confirmation(self, confirmation_id: str) -> Optional[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT confirmation_id, task_id, step_id, tool_name, arguments, status, created_at, expires_at "
                "FROM confirmations WHERE confirmation_id = ?",
                (confirmation_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            if row[5] == "pending" and datetime.fromisoformat(row[7]) <= utc_now():
                cursor.execute(
                    "UPDATE confirmations SET status = 'expired', updated_at = ? WHERE confirmation_id = ?",
                    (utc_now().isoformat(), confirmation_id),
                )
                conn.commit()
                row = (*row[:5], "expired", *row[6:])
            confirmation = self._confirmation_dict(row)
            cursor.execute("SELECT request_id FROM tasks WHERE task_id = ?", (confirmation["task_id"],))
            request_row = cursor.fetchone()
            confirmation["request_id"] = request_row[0] if request_row else None
            return confirmation

    def transition_confirmation(self, confirmation_id: str, new_status: str) -> Optional[dict]:
        now = utc_now()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                "SELECT confirmation_id, task_id, step_id, tool_name, arguments, status, created_at, expires_at "
                "FROM confirmations WHERE confirmation_id = ?",
                (confirmation_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            if row[5] != "pending":
                return {"confirmation_id": confirmation_id, "status": row[5], "transitioned": False}
            if datetime.fromisoformat(row[7]) <= now:
                new_status = "expired"
            cursor.execute(
                "UPDATE confirmations SET status = ?, updated_at = ? WHERE confirmation_id = ? AND status = 'pending'",
                (new_status, now.isoformat(), confirmation_id),
            )
            conn.commit()
        result = self.get_confirmation(confirmation_id)
        if result:
            result["transitioned"] = result["status"] == new_status
        return result

    def consume_confirmation(self, confirmation_id: str, task_id: str, step_id: str, tool_name: str, arguments: dict) -> bool:
        now = utc_now()
        arguments_json = json.dumps(arguments, sort_keys=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                "UPDATE confirmations SET status = 'executed', updated_at = ? "
                "WHERE confirmation_id = ? AND task_id = ? AND step_id = ? AND tool_name = ? "
                "AND arguments = ? AND status = 'approved' AND expires_at > ?",
                (now.isoformat(), confirmation_id, task_id, step_id, tool_name, arguments_json, now.isoformat()),
            )
            consumed = cursor.rowcount == 1
            conn.commit()
            return consumed

    def reset_confirmed_step(self, confirmation_id: str) -> Optional[dict]:
        confirmation = self.get_confirmation(confirmation_id)
        if not confirmation or confirmation["status"] != "approved":
            return confirmation
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT task_id, step_id FROM confirmations WHERE confirmation_id = ?", (confirmation_id,))
            row = cursor.fetchone()
            if not row:
                return None
            cursor.execute("UPDATE task_steps SET status = 'pending', error = NULL, updated_at = ? WHERE step_id = ?", (utc_now().isoformat(), row[1]))
            cursor.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE task_id = ? AND status = ?", (TaskStatus.READY, utc_now().isoformat(), row[0], TaskStatus.BLOCKED))
            conn.commit()
        return confirmation

    def transition_task(self, task_id: str, new_status: TaskStatus) -> TaskModel:
        task = self.get_task(task_id)
        if not task:
            raise ValueError("Task not found")

        # Legal transition logic
        valid_transitions = {
            TaskStatus.CREATED: [TaskStatus.PLANNING, TaskStatus.CANCELLED],
            TaskStatus.PLANNING: [TaskStatus.PLANNED, TaskStatus.REQUIRES_CLARIFICATION, TaskStatus.FAILED, TaskStatus.CANCELLED],
            TaskStatus.PLANNED: [TaskStatus.READY, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.ACTION_RESOLUTION_REQUIRED],
            TaskStatus.READY: [TaskStatus.RUNNING, TaskStatus.CANCELLED],
            TaskStatus.RUNNING: [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.BLOCKED, TaskStatus.ACTION_RESOLUTION_REQUIRED, TaskStatus.INTERRUPTED, TaskStatus.READY],
            TaskStatus.PAUSED: [TaskStatus.READY, TaskStatus.CANCELLED, TaskStatus.INTERRUPTED],
            TaskStatus.INTERRUPTED: [TaskStatus.READY, TaskStatus.CANCELLED],
            TaskStatus.REQUIRES_CLARIFICATION: [TaskStatus.CANCELLED],
            TaskStatus.ACTION_RESOLUTION_REQUIRED: [TaskStatus.CANCELLED],
            TaskStatus.BLOCKED: [TaskStatus.CANCELLED],
            TaskStatus.FAILED: [],
            TaskStatus.COMPLETED: [],
            TaskStatus.CANCELLED: []
        }

        if new_status not in valid_transitions.get(task.status, []):
            raise ValueError(f"Invalid transition from {task.status} to {new_status}")

        now = utc_now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tasks SET status = ?, updated_at = ? WHERE task_id = ?
            ''', (new_status, now, task_id))
            conn.commit()
            
        return self.get_task(task_id)

    def cancel_task(self, task_id: str) -> TaskModel:
        return self.transition_task(task_id, TaskStatus.CANCELLED)

    def update_step(self, step_id: str, status: Optional[str] = None, result: Optional[dict] = None, error: Optional[dict] = None) -> None:
        now = utc_now().isoformat()
        updates = ["updated_at = ?"]
        params = [now]
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if result is not None:
            updates.append("result = ?")
            params.append(json.dumps(result))
        if error is not None:
            updates.append("error = ?")
            params.append(json.dumps(error))
            
        params.append(step_id)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"UPDATE task_steps SET {', '.join(updates)} WHERE step_id = ?"
            cursor.execute(query, tuple(params))
            conn.commit()
