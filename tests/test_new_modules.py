import pytest
from datetime import datetime, timedelta
from pathlib import Path
import json
from unittest.mock import MagicMock, patch

from src.logger import SessionLogger
from src.llm.prompt_builder import PromptBuilder
from src.context import ContextManager
from src.models.base import Task, JournalEntry, CheckIn, Project, TaskStatus, Priority
from src.storage.data_store import DataStore

@pytest.fixture
def mock_data_store():
    return MagicMock(spec=DataStore)

@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path

@pytest.fixture
def session_logger(temp_dir):
    return SessionLogger(log_dir=str(temp_dir))

@pytest.fixture
def prompt_builder(mock_data_store, temp_dir):
    return PromptBuilder(mock_data_store, prompt_dir=str(temp_dir))

@pytest.fixture
def context_manager(mock_data_store, temp_dir):
    return ContextManager(mock_data_store, context_dir=str(temp_dir))

# Session Logger Tests
def test_session_logger_start_session(session_logger):
    session_id = session_logger.start_session("test_session")
    assert session_id is not None
    assert session_logger.current_session == session_id
    assert session_logger.sessions[session_id]["type"] == "test_session"

def test_session_logger_log_interaction(session_logger):
    session_id = session_logger.start_session("test_session")
    interaction = {"type": "test", "data": "test_data"}
    session_logger.log_interaction(session_id, interaction)
    assert len(session_logger.sessions[session_id]["interactions"]) == 1
    assert session_logger.sessions[session_id]["interactions"][0]["type"] == "test"
    assert session_logger.sessions[session_id]["interactions"][0]["data"] == "test_data"

def test_session_logger_end_session(session_logger):
    session_id = session_logger.start_session("test_session")
    session_logger.end_session(session_id)
    assert session_logger.current_session is None
    assert session_logger.sessions[session_id]["end_time"] is not None

def test_session_logger_save_sessions(session_logger, temp_dir):
    session_id = session_logger.start_session("test_session")
    session_logger.log_interaction(session_id, {"type": "test"})
    session_logger.end_session(session_id)
    
    sessions_file = temp_dir / "sessions.json"
    assert sessions_file.exists()
    sessions_data = json.loads(sessions_file.read_text())
    assert session_id in sessions_data
    assert sessions_data[session_id]["type"] == "test_session"

# Prompt Builder Tests
def test_prompt_builder_initialization(prompt_builder, temp_dir):
    assert prompt_builder.prompt_dir == temp_dir
    assert prompt_builder.prompt_versions_file == temp_dir / "versions.json"
    assert 1 in prompt_builder.prompt_versions
    assert "prompt" in prompt_builder.prompt_versions[1]

def test_prompt_builder_build_morning_prompt(prompt_builder, mock_data_store):
    mock_data_store.get_checkins_by_date.return_value = [
        CheckIn(
            type="morning",
            priorities=["priority1"],
            reflections=["reflection1"],
            tasks_completed=[],
            tasks_added=[],
            timestamp=datetime.now()
        )
    ]
    mock_data_store.get_journal_entries_by_date.return_value = [
        JournalEntry(
            content="test entry",
            reflection_type="reflection",
            mood="neutral",
            timestamp=datetime.now()
        )
    ]
    mock_data_store.get_all.return_value = [
        Task(
            title="test task",
            description="test description",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            created_at=datetime.now()
        )
    ]
    
    prompt = prompt_builder.build_morning_prompt()
    assert "morning coaching" in prompt.lower()
    assert "priority1" in prompt
    assert "test entry" in prompt
    assert "test task" in prompt

def test_prompt_builder_build_evening_prompt(prompt_builder, mock_data_store):
    mock_data_store.get_checkins_by_date.return_value = [
        CheckIn(
            type="evening",
            priorities=["priority1"],
            reflections=["reflection1"],
            tasks_completed=[],
            tasks_added=[],
            timestamp=datetime.now()
        )
    ]
    mock_data_store.get_journal_entries_by_date.return_value = [
        JournalEntry(
            content="test entry",
            reflection_type="reflection",
            mood="neutral",
            timestamp=datetime.now()
        )
    ]
    mock_data_store.get_all.return_value = [
        Task(
            title="test task",
            description="test description",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            created_at=datetime.now()
        )
    ]
    
    prompt = prompt_builder.build_evening_prompt()
    assert "evening coaching" in prompt.lower()
    assert "priority1" in prompt
    assert "test entry" in prompt
    assert "test task" in prompt

def test_prompt_builder_build_procrastination_prompt(prompt_builder):
    entry = JournalEntry(
        content="test content",
        reflection_type="procrastination",
        mood="frustrated",
        timestamp=datetime.now()
    )
    prompt = prompt_builder.build_procrastination_prompt(entry)
    assert "procrastination" in prompt.lower()
    assert "test content" in prompt
    assert "frustrated" in prompt

def test_prompt_builder_build_task_breakdown_prompt(prompt_builder):
    task = Task(
        title="test task",
        description="test description",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.HIGH,
        created_at=datetime.now()
    )
    prompt = prompt_builder.build_task_breakdown_prompt(task)
    assert "break down" in prompt.lower()
    assert "test task" in prompt
    assert "test description" in prompt
    assert "high" in prompt

def test_prompt_builder_update_system_prompt(prompt_builder, temp_dir):
    changes = {
        "morning_prompt": {
            "current_score": 0.7,
            "issues": ["clarity"],
            "suggested_changes": {
                "clarity": {
                    "add": ["Be more specific with task recommendations."],
                    "remove": []
                }
            }
        }
    }
    prompt_builder.update_system_prompt(changes)
    # Make sure the prompt versions have been updated
    assert len(prompt_builder.prompt_versions) > 1
    latest_version = max(prompt_builder.prompt_versions.keys())
    assert "changes" in prompt_builder.prompt_versions[latest_version]

# Context Manager Tests
def test_context_manager_initialization(context_manager, temp_dir):
    assert context_manager.context_dir == temp_dir
    assert context_manager.context_file == temp_dir / "context.json"
    assert "user" in context_manager.context
    assert "assistant" in context_manager.context

def test_context_manager_update_user_goals(context_manager):
    goals = ["goal1", "goal2"]
    context_manager.update_user_goals(goals)
    assert context_manager.context["user"]["goals"] == goals

def test_context_manager_update_user_preferences(context_manager):
    preferences = {"pref1": "value1"}
    context_manager.update_user_preferences(preferences)
    assert context_manager.context["user"]["preferences"]["pref1"] == "value1"

def test_context_manager_add_to_assistant_memory(context_manager):
    memory_item = {"type": "test", "data": "test_data"}
    context_manager.add_to_assistant_memory(memory_item)
    assert len(context_manager.context["assistant"]["memory"]) == 1
    assert "timestamp" in context_manager.context["assistant"]["memory"][0]
    assert context_manager.context["assistant"]["memory"][0]["type"] == "test"

def test_context_manager_get_recent_context(context_manager, mock_data_store):
    now = datetime.now()
    mock_data_store.get_all.side_effect = [
        [Task(
            title="test task",
            description="test description",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            created_at=now
        )],
        [JournalEntry(
            content="test entry",
            reflection_type="reflection",
            mood="neutral",
            timestamp=now
        )],
        [CheckIn(
            type="morning",
            priorities=["priority1"],
            reflections=["reflection1"],
            tasks_completed=[],
            tasks_added=[],
            timestamp=now
        )]
    ]
    
    context = context_manager.get_recent_context()
    assert "tasks" in context
    assert "journal_entries" in context
    assert "check_ins" in context
    assert "user_goals" in context
    assert "user_patterns" in context
    assert "assistant_memory" in context

def test_context_manager_analyze_productivity_patterns(context_manager, mock_data_store):
    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)
    
    mock_data_store.get_all.side_effect = [
        [Task(
            title="task1",
            description="description1",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            created_at=now
        ),
         Task(
            title="task2",
            description="description2",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
            created_at=now
        )],
        [JournalEntry(
            content="I'm overwhelmed",
            reflection_type="procrastination",
            mood="frustrated",
            timestamp=now
        )],
        [CheckIn(
            type="morning",
            priorities=["priority1"],
            reflections=["reflection1"],
            tasks_completed=[],
            tasks_added=[],
            timestamp=now
        )]
    ]
    
    patterns = context_manager.analyze_productivity_patterns()
    assert "task_completion_rate" in patterns
    assert patterns["task_completion_rate"] == 0.5
    assert "common_procrastination_triggers" in patterns
    assert "task_overwhelm" in patterns["common_procrastination_triggers"]
    assert "productive_times" in patterns
    assert "goal_progress" in patterns 