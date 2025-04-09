import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.llm.coach import ProductivityCoach
from src.models.base import JournalEntry, Task
from src.storage.data_store import DataStore


@pytest.fixture
def mock_data_store():
    """Create a mock DataStore."""
    data_store = MagicMock(spec=DataStore)
    return data_store


@pytest.fixture
def coach(mock_data_store):
    """Create a ProductivityCoach with a mock DataStore."""
    with patch("src.llm.coach.OpenAI") as mock_openai:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"}):
            coach = ProductivityCoach(mock_data_store)
            coach.client = MagicMock()
            yield coach


def test_coach_initialization(coach):
    """Test that ProductivityCoach initializes correctly."""
    assert coach.data_store is not None
    assert coach.system_prompt is not None
    assert "productivity coach" in coach.system_prompt.lower()


def test_get_context(coach, mock_data_store):
    """Test that _get_context gathers the correct information."""
    # Mock the data store methods
    mock_data_store.get_checkins_by_date.return_value = []
    mock_data_store.get_journal_entries_by_date.return_value = []
    mock_data_store.get_all.return_value = []
    
    # Call the method
    context = coach._get_context()
    
    # Check that the data store methods were called
    mock_data_store.get_checkins_by_date.assert_called_once()
    mock_data_store.get_journal_entries_by_date.assert_called_once()
    mock_data_store.get_all.assert_called_once()
    
    # Check that the context is a string
    assert isinstance(context, str)


def test_get_morning_coaching(coach):
    """Test that get_morning_coaching calls the OpenAI API correctly."""
    # Mock the OpenAI API response
    coach.client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Morning coaching insights"))]
    )
    
    # Mock the _get_context method
    coach._get_context = MagicMock(return_value="Test context")
    
    # Call the method
    result = coach.get_morning_coaching()
    
    # Check that the OpenAI API was called correctly
    coach.client.chat.completions.create.assert_called_once()
    call_args = coach.client.chat.completions.create.call_args[1]
    assert call_args["model"] == "gpt-3.5-turbo"
    assert len(call_args["messages"]) == 2
    assert call_args["messages"][0]["role"] == "system"
    assert call_args["messages"][1]["role"] == "user"
    assert "morning coaching" in call_args["messages"][1]["content"].lower()
    
    # Check that the result is the expected string
    assert result == "Morning coaching insights"


def test_get_evening_coaching(coach):
    """Test that get_evening_coaching calls the OpenAI API correctly."""
    # Mock the OpenAI API response
    coach.client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Evening coaching insights"))]
    )
    
    # Mock the _get_context method
    coach._get_context = MagicMock(return_value="Test context")
    
    # Call the method
    result = coach.get_evening_coaching()
    
    # Check that the OpenAI API was called correctly
    coach.client.chat.completions.create.assert_called_once()
    call_args = coach.client.chat.completions.create.call_args[1]
    assert call_args["model"] == "gpt-3.5-turbo"
    assert len(call_args["messages"]) == 2
    assert call_args["messages"][0]["role"] == "system"
    assert call_args["messages"][1]["role"] == "user"
    assert "evening coaching" in call_args["messages"][1]["content"].lower()
    
    # Check that the result is the expected string
    assert result == "Evening coaching insights"


def test_analyze_procrastination(coach):
    """Test that analyze_procrastination calls the OpenAI API correctly."""
    # Create a journal entry
    entry = JournalEntry(
        content="I'm procrastinating on my task",
        reflection_type="procrastination",
        mood="anxious",
    )
    
    # Mock the OpenAI API response
    coach.client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Procrastination analysis"))]
    )
    
    # Call the method
    result = coach.analyze_procrastination(entry)
    
    # Check that the OpenAI API was called correctly
    coach.client.chat.completions.create.assert_called_once()
    call_args = coach.client.chat.completions.create.call_args[1]
    assert call_args["model"] == "gpt-3.5-turbo"
    assert len(call_args["messages"]) == 2
    assert call_args["messages"][0]["role"] == "system"
    assert call_args["messages"][1]["role"] == "user"
    assert "procrastination" in call_args["messages"][1]["content"].lower()
    assert entry.content in call_args["messages"][1]["content"]
    
    # Check that the result is the expected string
    assert result == "Procrastination analysis"


def test_suggest_task_breakdown(coach):
    """Test that suggest_task_breakdown calls the OpenAI API correctly."""
    # Create a task
    task = Task(
        title="Complex Task",
        description="This is a complex task that needs to be broken down",
        priority="high",
    )
    
    # Mock the OpenAI API response
    coach.client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="- Subtask 1\n- Subtask 2\n- Subtask 3"))]
    )
    
    # Call the method
    result = coach.suggest_task_breakdown(task)
    
    # Check that the OpenAI API was called correctly
    coach.client.chat.completions.create.assert_called_once()
    call_args = coach.client.chat.completions.create.call_args[1]
    assert call_args["model"] == "gpt-3.5-turbo"
    assert len(call_args["messages"]) == 2
    assert call_args["messages"][0]["role"] == "system"
    assert call_args["messages"][1]["role"] == "user"
    assert "break down" in call_args["messages"][1]["content"].lower()
    assert task.title in call_args["messages"][1]["content"]
    
    # Check that the result is a list of subtasks
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0] == "Subtask 1"
    assert result[1] == "Subtask 2"
    assert result[2] == "Subtask 3"


def test_update_system_prompt(coach):
    """Test that update_system_prompt calls the OpenAI API correctly."""
    # Store the original prompt
    original_prompt = coach.system_prompt
    
    # Mock the OpenAI API response
    coach.client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Updated system prompt"))]
    )
    
    # Call the method
    coach.update_system_prompt("The coaching is too generic")
    
    # Check that the OpenAI API was called correctly
    coach.client.chat.completions.create.assert_called_once()
    call_args = coach.client.chat.completions.create.call_args[1]
    assert call_args["model"] == "gpt-3.5-turbo"
    assert len(call_args["messages"]) == 2
    assert call_args["messages"][0]["role"] == "system"
    assert call_args["messages"][0]["content"] == "You are a prompt engineering expert."
    assert call_args["messages"][1]["role"] == "user"
    assert "feedback" in call_args["messages"][1]["content"].lower()
    assert "The coaching is too generic" in call_args["messages"][1]["content"]
    assert original_prompt in call_args["messages"][1]["content"]
    
    # Check that the system prompt was updated
    assert coach.system_prompt == "Updated system prompt" 