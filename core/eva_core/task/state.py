import sqlite3
import json
import logging
from typing import Optional, List
from datetime import datetime
from core.eva_core.protocol import TaskModel, TaskStatus, TaskStep, utc_now
from core.eva_core.database import DB_PATH

class TaskStateManager:
    def _get_connection(self):
        return sqlite3.connect(DB_PATH)

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
            cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
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

            cursor.execute('SELECT * FROM task_steps WHERE task_id = ? ORDER BY sequence ASC', (task_id,))
            step_rows = cursor.fetchall()
            for s_row in step_rows:
                step = TaskStep(
                    step_id=s_row[0],
                    task_id=s_row[1],
                    sequence=s_row[2],
                    description=s_row[3],
                    dependencies=json.loads(s_row[4]) if s_row[4] else [],
                    status=s_row[5],
                    result=json.loads(s_row[6]) if s_row[6] else None,
                    error=json.loads(s_row[7]) if s_row[7] else None,
                    created_at=datetime.fromisoformat(s_row[8]),
                    updated_at=datetime.fromisoformat(s_row[9])
                )
                task.steps.append(step)
            return task

    def save_plan(self, task_id: str, steps: List[TaskStep]) -> TaskModel:
        task = self.get_task(task_id)
        if not task:
            raise ValueError("Task not found")
        
        now = utc_now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for step in steps:
                cursor.execute('''
                    INSERT INTO task_steps (step_id, task_id, sequence, description, dependencies, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (step.step_id, step.task_id, step.sequence, step.description, json.dumps(step.dependencies), step.status, step.created_at.isoformat(), step.updated_at.isoformat()))
            
            total_steps = len(steps)
            cursor.execute('''
                UPDATE tasks SET total_steps = ?, updated_at = ? WHERE task_id = ?
            ''', (total_steps, now, task_id))
            conn.commit()
            
        return self.get_task(task_id)

    def transition_task(self, task_id: str, new_status: TaskStatus) -> TaskModel:
        task = self.get_task(task_id)
        if not task:
            raise ValueError("Task not found")

        # Legal transition logic
        valid_transitions = {
            TaskStatus.CREATED: [TaskStatus.PLANNING, TaskStatus.CANCELLED],
            TaskStatus.PLANNING: [TaskStatus.PLANNED, TaskStatus.REQUIRES_CLARIFICATION, TaskStatus.FAILED, TaskStatus.CANCELLED],
            TaskStatus.PLANNED: [TaskStatus.READY, TaskStatus.CANCELLED],
            TaskStatus.READY: [TaskStatus.RUNNING, TaskStatus.CANCELLED],
            TaskStatus.RUNNING: [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED],
            TaskStatus.REQUIRES_CLARIFICATION: [TaskStatus.CANCELLED],
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
