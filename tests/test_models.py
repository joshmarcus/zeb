from datetime import datetime
from uuid import UUID

import pytest

from src.models.base import CheckIn, JournalEntry, Priority, Project, Task, TaskStatus


def test_task_creation():
    task = Task(
        title="Test Task",
        description="Test Description",
        priority=Priority.HIGH,
        due_date=datetime.now(),
    )
    
    assert task.title == "Test Task"
    assert task.description == "Test Description"
    assert task.priority == Priority.HIGH
    assert task.status == TaskStatus.PENDING
    assert isinstance(task.id, UUID)
    assert len(task.subtasks) == 0
    assert len(task.tags) == 0
    assert len(task.notes) == 0


def test_project_creation():
    project = Project(
        name="Test Project",
        description="Test Description",
    )
    
    assert project.name == "Test Project"
    assert project.description == "Test Description"
    assert project.status == TaskStatus.PENDING
    assert isinstance(project.id, UUID)
    assert len(project.tasks) == 0
    assert len(project.tags) == 0


def test_journal_entry_creation():
    entry = JournalEntry(
        content="Test Journal Entry",
        reflection_type="reflection",
        mood="productive",
    )
    
    assert entry.content == "Test Journal Entry"
    assert entry.reflection_type == "reflection"
    assert entry.mood == "productive"
    assert isinstance(entry.id, UUID)
    assert isinstance(entry.timestamp, datetime)
    assert len(entry.tags) == 0
    assert len(entry.related_tasks) == 0


def test_checkin_creation():
    checkin = CheckIn(
        type="morning",
        priorities=["Priority 1", "Priority 2"],
        reflections=["Reflection 1"],
        tasks_completed=[],
        tasks_added=[],
    )
    
    assert checkin.type == "morning"
    assert len(checkin.priorities) == 2
    assert len(checkin.reflections) == 1
    assert isinstance(checkin.id, UUID)
    assert isinstance(checkin.timestamp, datetime)
    assert len(checkin.tasks_completed) == 0
    assert len(checkin.tasks_added) == 0
    assert len(checkin.notes) == 0


def test_task_with_subtasks():
    subtask = Task(title="Subtask 1")
    task = Task(
        title="Parent Task",
        subtasks=[subtask],
    )
    
    assert len(task.subtasks) == 1
    assert task.subtasks[0].title == "Subtask 1"
    assert task.subtasks[0].status == TaskStatus.PENDING


def test_project_with_tasks():
    task = Task(title="Project Task")
    project = Project(
        name="Test Project",
        tasks=[task],
    )
    
    assert len(project.tasks) == 1
    assert project.tasks[0].title == "Project Task"
    assert project.tasks[0].status == TaskStatus.PENDING 