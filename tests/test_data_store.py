import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from src.models.base import CheckIn, JournalEntry, Project, Task
from src.storage.data_store import DataStore


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def data_store(temp_data_dir):
    """Create a DataStore instance with a temporary data directory."""
    return DataStore(data_dir=temp_data_dir)


def test_data_store_initialization(temp_data_dir):
    """Test that DataStore creates necessary files on initialization."""
    data_store = DataStore(data_dir=temp_data_dir)
    
    # Check that data directory exists
    assert os.path.exists(temp_data_dir)
    
    # Check that all required files exist
    assert os.path.exists(os.path.join(temp_data_dir, "tasks.json"))
    assert os.path.exists(os.path.join(temp_data_dir, "projects.json"))
    assert os.path.exists(os.path.join(temp_data_dir, "journal.json"))
    assert os.path.exists(os.path.join(temp_data_dir, "checkins.json"))
    
    # Check that files contain empty lists
    with open(os.path.join(temp_data_dir, "tasks.json"), "r") as f:
        assert json.load(f) == []
    
    with open(os.path.join(temp_data_dir, "projects.json"), "r") as f:
        assert json.load(f) == []


def test_save_and_get_task(data_store):
    """Test saving and retrieving a task."""
    task = Task(
        title="Test Task",
        description="Test Description",
    )
    
    # Save the task
    data_store.save(task)
    
    # Retrieve the task by ID
    retrieved_task = data_store.get_by_id(Task, task.id)
    
    # Check that the retrieved task matches the original
    assert retrieved_task is not None
    assert retrieved_task.title == task.title
    assert retrieved_task.description == task.description
    assert retrieved_task.id == task.id


def test_save_and_get_project(data_store):
    """Test saving and retrieving a project."""
    project = Project(
        name="Test Project",
        description="Test Description",
    )
    
    # Save the project
    data_store.save(project)
    
    # Retrieve the project by ID
    retrieved_project = data_store.get_by_id(Project, project.id)
    
    # Check that the retrieved project matches the original
    assert retrieved_project is not None
    assert retrieved_project.name == project.name
    assert retrieved_project.description == project.description
    assert retrieved_project.id == project.id


def test_save_and_get_journal_entry(data_store):
    """Test saving and retrieving a journal entry."""
    entry = JournalEntry(
        content="Test Journal Entry",
        reflection_type="reflection",
    )
    
    # Save the journal entry
    data_store.save(entry)
    
    # Retrieve the journal entry by ID
    retrieved_entry = data_store.get_by_id(JournalEntry, entry.id)
    
    # Check that the retrieved journal entry matches the original
    assert retrieved_entry is not None
    assert retrieved_entry.content == entry.content
    assert retrieved_entry.reflection_type == entry.reflection_type
    assert retrieved_entry.id == entry.id


def test_save_and_get_checkin(data_store):
    """Test saving and retrieving a check-in."""
    checkin = CheckIn(
        type="morning",
        priorities=["Priority 1"],
        reflections=["Reflection 1"],
        tasks_completed=[],
        tasks_added=[],
    )
    
    # Save the check-in
    data_store.save(checkin)
    
    # Retrieve the check-in by ID
    retrieved_checkin = data_store.get_by_id(CheckIn, checkin.id)
    
    # Check that the retrieved check-in matches the original
    assert retrieved_checkin is not None
    assert retrieved_checkin.type == checkin.type
    assert retrieved_checkin.priorities == checkin.priorities
    assert retrieved_checkin.reflections == checkin.reflections
    assert retrieved_checkin.id == checkin.id


def test_get_all_tasks(data_store):
    """Test retrieving all tasks."""
    # Create and save multiple tasks
    tasks = [
        Task(title=f"Task {i}", description=f"Description {i}")
        for i in range(3)
    ]
    
    for task in tasks:
        data_store.save(task)
    
    # Retrieve all tasks
    retrieved_tasks = data_store.get_all(Task)
    
    # Check that all tasks were retrieved
    assert len(retrieved_tasks) == len(tasks)
    
    # Check that each task was retrieved correctly
    for task in tasks:
        assert any(retrieved.id == task.id for retrieved in retrieved_tasks)


def test_delete_task(data_store):
    """Test deleting a task."""
    task = Task(title="Task to Delete")
    data_store.save(task)
    
    # Delete the task
    result = data_store.delete(Task, task.id)
    
    # Check that deletion was successful
    assert result is True
    
    # Check that the task no longer exists
    assert data_store.get_by_id(Task, task.id) is None


def test_get_tasks_by_project(data_store):
    """Test retrieving tasks by project."""
    # Create a project
    project = Project(name="Test Project")
    data_store.save(project)
    
    # Create tasks associated with the project
    project_tasks = [
        Task(title=f"Project Task {i}", project_id=project.id)
        for i in range(2)
    ]
    
    # Create tasks not associated with the project
    other_tasks = [
        Task(title=f"Other Task {i}")
        for i in range(2)
    ]
    
    # Save all tasks
    for task in project_tasks + other_tasks:
        data_store.save(task)
    
    # Retrieve tasks by project
    retrieved_tasks = data_store.get_tasks_by_project(project.id)
    
    # Check that only project tasks were retrieved
    assert len(retrieved_tasks) == len(project_tasks)
    
    # Check that each project task was retrieved correctly
    for task in project_tasks:
        assert any(retrieved.id == task.id for retrieved in retrieved_tasks)


def test_get_journal_entries_by_date(data_store):
    """Test retrieving journal entries by date."""
    # Create journal entries with different dates
    today = datetime.now()
    yesterday = datetime(2023, 1, 1)
    
    today_entries = [
        JournalEntry(
            content=f"Today Entry {i}",
            reflection_type="reflection",
            timestamp=today,
        )
        for i in range(2)
    ]
    
    yesterday_entries = [
        JournalEntry(
            content=f"Yesterday Entry {i}",
            reflection_type="reflection",
            timestamp=yesterday,
        )
        for i in range(2)
    ]
    
    # Save all entries
    for entry in today_entries + yesterday_entries:
        data_store.save(entry)
    
    # Retrieve entries by today's date
    retrieved_entries = data_store.get_journal_entries_by_date(today)
    
    # Check that only today's entries were retrieved
    assert len(retrieved_entries) == len(today_entries)
    
    # Check that each today entry was retrieved correctly
    for entry in today_entries:
        assert any(retrieved.id == entry.id for retrieved in retrieved_entries)


def test_get_checkins_by_date(data_store):
    """Test retrieving check-ins by date."""
    # Create check-ins with different dates
    today = datetime.now()
    yesterday = datetime(2023, 1, 1)
    
    today_checkins = [
        CheckIn(
            type="morning",
            priorities=["Priority"],
            reflections=["Reflection"],
            tasks_completed=[],
            tasks_added=[],
            timestamp=today,
        )
        for i in range(2)
    ]
    
    yesterday_checkins = [
        CheckIn(
            type="morning",
            priorities=["Priority"],
            reflections=["Reflection"],
            tasks_completed=[],
            tasks_added=[],
            timestamp=yesterday,
        )
        for i in range(2)
    ]
    
    # Save all check-ins
    for checkin in today_checkins + yesterday_checkins:
        data_store.save(checkin)
    
    # Retrieve check-ins by today's date
    retrieved_checkins = data_store.get_checkins_by_date(today)
    
    # Check that only today's check-ins were retrieved
    assert len(retrieved_checkins) == len(today_checkins)
    
    # Check that each today check-in was retrieved correctly
    for checkin in today_checkins:
        assert any(retrieved.id == checkin.id for retrieved in retrieved_checkins) 