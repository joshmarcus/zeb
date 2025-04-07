from unittest.mock import MagicMock, patch, ANY
from datetime import datetime

import pytest
from typer.testing import CliRunner

from src.main import app
from src.models.base import Task, JournalEntry, CheckIn, Project, TaskStatus, Priority, FeatureRequest, FeatureStatus
from src.storage.data_store import DataStore
from src.llm.coach import ProductivityCoach
from src.llm.prompt_builder import PromptBuilder
from src.context import ContextManager
from src.logger import SessionLogger


@pytest.fixture
def runner():
    """Create a Typer CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_data_store():
    """Create a mock DataStore."""
    with patch("src.main.data_store") as mock:
        yield mock


@pytest.fixture
def mock_coach():
    """Create a mock ProductivityCoach."""
    with patch("src.main.coach") as mock:
        yield mock


@pytest.fixture
def mock_prompt_builder():
    """Create a mock PromptBuilder."""
    with patch("src.main.prompt_builder") as mock:
        yield mock


@pytest.fixture
def mock_context_manager():
    """Create a mock ContextManager."""
    with patch("src.main.context_manager") as mock:
        yield mock


@pytest.fixture
def mock_session_logger():
    """Create a mock SessionLogger."""
    with patch("src.main.session_logger") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_openai():
    """Mock OpenAI client to prevent API calls during tests."""
    with patch("openai.OpenAI") as mock:
        client = MagicMock()
        chat_completion = MagicMock()
        chat_completion.choices = [MagicMock(message=MagicMock(content="Mocked response"))]
        client.chat.completions.create.return_value = chat_completion
        mock.return_value = client
        yield client


def test_check_in_morning(runner, mock_data_store, mock_coach, mock_prompt_builder, mock_context_manager, mock_session_logger):
    """Test the check-in morning command."""
    mock_session_logger.start_session.return_value = "test_session"
    mock_context_manager.get_recent_context.return_value = {"tasks": []}
    mock_prompt_builder.build_morning_prompt.return_value = "Test morning prompt"
    mock_coach.get_morning_coaching.return_value = "Morning coaching response"
    
    result = runner.invoke(app, ["check-in-morning"])
    
            assert result.exit_code == 0
    mock_session_logger.start_session.assert_called_once_with("morning_check_in")
    mock_context_manager.get_recent_context.assert_called_once()
    mock_prompt_builder.build_morning_prompt.assert_called_once()
    mock_coach.get_morning_coaching.assert_called_once_with("Test morning prompt", {"tasks": []})
    mock_session_logger.log_interaction.assert_called_once()
    mock_session_logger.end_session.assert_called_once_with("test_session")


def test_check_in_evening(runner, mock_data_store, mock_coach, mock_prompt_builder, mock_context_manager, mock_session_logger):
    """Test the check-in evening command."""
    mock_session_logger.start_session.return_value = "test_session"
    mock_context_manager.get_recent_context.return_value = {"tasks": []}
    mock_prompt_builder.build_evening_prompt.return_value = "Test evening prompt"
    mock_coach.get_evening_coaching.return_value = "Evening coaching response"
    
    result = runner.invoke(app, ["check-in-evening"])
    
            assert result.exit_code == 0
    mock_session_logger.start_session.assert_called_once_with("evening_check_in")
    mock_context_manager.get_recent_context.assert_called_once()
    mock_prompt_builder.build_evening_prompt.assert_called_once()
    mock_coach.get_evening_coaching.assert_called_once_with("Test evening prompt", {"tasks": []})
    mock_session_logger.log_interaction.assert_called_once()
    mock_session_logger.end_session.assert_called_once_with("test_session")


def test_task_add(runner, mock_data_store, mock_coach, mock_prompt_builder, mock_session_logger):
    """Test the task add command."""
    mock_session_logger.start_session.return_value = "test_session"
    mock_coach.suggest_task_breakdown.return_value = ["Subtask 1", "Subtask 2"]
    
    result = runner.invoke(app, ["task", "--action", "add"], input="Test Task\nTest Description\nhigh\n2024-03-20\ny\n")
    
            assert result.exit_code == 0
    mock_session_logger.start_session.assert_called_once_with("task_add")
            mock_coach.suggest_task_breakdown.assert_called_once()
    mock_session_logger.log_interaction.assert_called_once()
    mock_session_logger.end_session.assert_called_once_with("test_session")


def test_task_list(runner, mock_data_store, mock_session_logger):
    """Test the task list command."""
    mock_session_logger.start_session.return_value = "test_session"
    mock_data_store.get_all.return_value = [
        Task(
            title="Test Task",
            description="Test Description",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH
        )
    ]
    
            result = runner.invoke(app, ["task", "--action", "list"])
            
            assert result.exit_code == 0
    mock_session_logger.start_session.assert_called_once_with("task_list")
    mock_data_store.get_all.assert_called_once_with(Task)
    mock_session_logger.log_interaction.assert_called_once()
    mock_session_logger.end_session.assert_called_once_with("test_session")


def test_journal_add(runner, mock_data_store, mock_coach, mock_prompt_builder, mock_session_logger):
    """Test the journal add command."""
    mock_session_logger.start_session.return_value = "test_session"
    mock_prompt_builder.build_procrastination_prompt.return_value = "Test procrastination prompt"
    mock_coach.analyze_procrastination.return_value = "Procrastination insights"
    
    result = runner.invoke(app, ["journal", "--content", "Test content", "--reflection-type", "procrastination", "--mood", "frustrated"])
    
            assert result.exit_code == 0
    mock_session_logger.start_session.assert_called_once_with("journal_add")
    mock_prompt_builder.build_procrastination_prompt.assert_called_once()
    mock_coach.analyze_procrastination.assert_called_once_with("Test procrastination prompt")
    assert mock_session_logger.log_interaction.call_count == 2
    mock_session_logger.end_session.assert_called_once_with("test_session")


def test_project_add(runner, mock_data_store, mock_session_logger):
    """Test the project add command."""
    mock_session_logger.start_session.return_value = "test_session"
    
    result = runner.invoke(app, ["project", "--action", "add"], input="Test Project\nTest Description\n")
    
            assert result.exit_code == 0
    mock_session_logger.start_session.assert_called_once_with("project_add")
            mock_data_store.save.assert_called_once()
    mock_session_logger.log_interaction.assert_called_once()
    mock_session_logger.end_session.assert_called_once_with("test_session")


def test_project_list(runner, mock_data_store, mock_session_logger):
    """Test the project list command."""
    mock_session_logger.start_session.return_value = "test_session"
    mock_data_store.get_all.return_value = [
        Project(
            name="Test Project",
            description="Test Description"
        )
    ]
    
            result = runner.invoke(app, ["project", "--action", "list"])
            
    assert result.exit_code == 0
    mock_session_logger.start_session.assert_called_once_with("project_list")
    mock_data_store.get_all.assert_called_once_with(Project)
    mock_session_logger.log_interaction.assert_called_once()
    mock_session_logger.end_session.assert_called_once_with("test_session")


def test_analyze_patterns(runner, mock_context_manager, mock_session_logger):
    """Test the analyze patterns command."""
    mock_session_logger.start_session.return_value = "test_session"
    mock_context_manager.analyze_productivity_patterns.return_value = {
        "task_completion_rate": 0.75,
        "common_procrastination_triggers": ["task_overwhelm"],
        "productive_times": {"most_productive_hours": [(9, 5), (14, 3)]},
        "goal_progress": {
            "Test Goal": {
                "completed_tasks": 3,
                "total_tasks": 5,
                "journal_mentions": 2
            }
        }
    }
    
    result = runner.invoke(app, ["analyze-patterns"])
    
    assert result.exit_code == 0
    mock_session_logger.start_session.assert_called_once_with("pattern_analysis")
    mock_context_manager.analyze_productivity_patterns.assert_called_once()
    mock_session_logger.log_interaction.assert_called_once()
    mock_session_logger.end_session.assert_called_once_with("test_session")


def test_feedback(runner, mock_prompt_builder, mock_context_manager, mock_session_logger):
    """Test the feedback command."""
    mock_session_logger.start_session.return_value = "test_session"
    mock_prompt_builder.update_system_prompt.return_value = "Updated system prompt"
    
    result = runner.invoke(app, ["feedback", "--content", "Test feedback", "--rating", "5"])
    
    assert result.exit_code == 0
    mock_session_logger.start_session.assert_called_once_with("feedback")
    mock_prompt_builder.update_system_prompt.assert_called_once_with("Test feedback")
    mock_context_manager.update_assistant_adaptations.assert_called_once()
    mock_session_logger.log_interaction.assert_called_once()
    mock_session_logger.end_session.assert_called_once_with("test_session")


def test_prompt_adaptation():
    """Test prompt adaptation functionality."""
    # Setup
    data_store = MockDataStore()
    prompt_builder = PromptBuilder(data_store)
    coach = ProductivityCoach(data_store)
    
    # Test morning prompt adaptation
    morning_context = {
        "check_ins": [
            {
                "type": "morning",
                "priorities": ["unclear task", "need to do something"],
                "timestamp": "2024-02-20T09:00:00"
            },
            {
                "type": "morning",
                "priorities": [],  # No priorities set
                "timestamp": "2024-02-21T09:00:00"
            }
        ],
        "journal_entries": []
    }
    
    # Test prompt effectiveness analysis
    effectiveness = coach._analyze_prompt_effectiveness(morning_context)
    assert effectiveness is not None
    assert "morning_prompt" in effectiveness
    assert effectiveness["morning_prompt"]["current_score"] < 0.7  # Should be low due to unclear tasks
    assert "Tasks often lack clarity" in effectiveness["morning_prompt"]["issues"]
    
    # Test evening prompt adaptation
    evening_context = {
        "check_ins": [
            {
                "type": "evening",
                "priorities": ["task1"],  # Shallow reflection
                "timestamp": "2024-02-20T17:00:00"
            },
            {
                "type": "evening",
                "priorities": ["task2"],  # No progress tracking
                "timestamp": "2024-02-21T17:00:00"
            }
        ],
        "journal_entries": []
    }
    
    effectiveness = coach._analyze_prompt_effectiveness(evening_context)
    assert effectiveness is not None
    assert "evening_prompt" in effectiveness
    assert effectiveness["evening_prompt"]["current_score"] < 0.7  # Should be low due to shallow reflections
    assert "Reflections lack depth" in effectiveness["evening_prompt"]["issues"]
    
    # Test task breakdown adaptation
    task_context = {
        "tasks": [
            {
                "title": "Complex Task",
                "status": "in_progress",
                "subtasks": ["todo something", "need to do another thing"]
            }
        ]
    }
    
    effectiveness = coach._analyze_prompt_effectiveness(task_context)
    assert effectiveness is not None
    assert "task_breakdown_prompt" in effectiveness
    assert effectiveness["task_breakdown_prompt"]["current_score"] < 0.7  # Should be low due to vague subtasks
    assert "Subtasks often lack specificity" in effectiveness["task_breakdown_prompt"]["issues"]
    
    # Test prompt improvement generation
    improvements = coach._generate_prompt_improvements(
        "morning_prompt",
        ["task_clarity", "priority_setting"]
    )
    assert "add" in improvements["task_clarity"]
    assert "remove" in improvements["task_clarity"]
    assert "add" in improvements["priority_setting"]
    assert "remove" in improvements["priority_setting"]
    
    # Test prompt changes application
    prompt_changes = {
        "morning_prompt": {
            "current_score": 0.6,
            "issues": ["task_clarity"],
            "suggested_changes": improvements
        }
    }
    
    # Mock the context manager
    coach.context_manager = MockContextManager()
    
    # Apply adaptations
    coach.apply_adaptations({"prompt_changes": prompt_changes})
    
    # Verify prompt changes were logged
    assert len(coach.context_manager.memory) == 1
    memory_entry = coach.context_manager.memory[0]
    assert memory_entry["type"] == "prompt_adaptation"
    assert memory_entry["prompt_type"] == "morning_prompt"
    assert memory_entry["changes"] == prompt_changes["morning_prompt"]


def test_prompt_builder_adaptation():
    """Test PromptBuilder's adaptation functionality."""
    # Setup
    data_store = MockDataStore()
    prompt_builder = PromptBuilder(data_store)
    
    # Test prompt effectiveness tracking
    effectiveness = prompt_builder.get_prompt_effectiveness("morning_prompt")
    assert "score" in effectiveness
    assert "history" in effectiveness
    
    # Test prompt updates
    changes = {
        "morning_prompt": {
            "current_score": 0.8,
            "issues": ["task_clarity"],
            "suggested_changes": {
                "task_clarity": {
                    "add": ["New prompt element"],
                    "remove": ["Old prompt element"]
                }
            }
        }
    }
    
    prompt_builder.update_system_prompt(changes)
    
    # Verify new version was created
    assert len(prompt_builder.prompt_versions) > 1
    latest_version = max(prompt_builder.prompt_versions.keys())
    assert "changes" in prompt_builder.prompt_versions[latest_version]
    
    # Test rollback functionality
    original_version = min(prompt_builder.prompt_versions.keys())
    prompt_builder.rollback_prompt(original_version)
    
    # Verify rollback created new version
    assert len(prompt_builder.prompt_versions) > 2
    rollback_version = max(prompt_builder.prompt_versions.keys())
    assert prompt_builder.prompt_versions[rollback_version]["changes"]["type"] == "rollback"


class MockContextManager:
    """Mock context manager for testing."""
    def __init__(self):
        self.memory = []
        
    def add_to_assistant_memory(self, entry):
        self.memory.append(entry)
        
    def update_assistant_adaptations(self, adaptations):
        pass
        
    def get_recent_context(self, days=7):
        return {
            "tasks": [],
            "check_ins": [],
            "journal_entries": []
        }


class MockDataStore:
    """Mock data store for testing."""
    def __init__(self):
        self.items = {}
        
    def save(self, item):
        item_type = type(item)
        if item_type not in self.items:
            self.items[item_type] = []
        self.items[item_type].append(item)
        
    def get_all(self, item_type):
        return self.items.get(item_type, [])
        
    def get_by_id(self, item_type, item_id):
        items = self.items.get(item_type, [])
        for item in items:
            if str(item.id) == str(item_id):
                return item
        return None
        
    def delete(self, item_type, item_id):
        items = self.items.get(item_type, [])
        self.items[item_type] = [item for item in items if str(item.id) != str(item_id)]


def test_feature_request():
    """Test feature request functionality."""
    # Setup
    data_store = MockDataStore()
    
    # Test feature creation
    feature = FeatureRequest(
        title="Test Feature",
        description="A test feature request",
        priority=Priority.MEDIUM,
        tags=["test", "feature"]
    )
    data_store.save(feature)
    
    # Test feature retrieval
    features = data_store.get_all(FeatureRequest)
    assert len(features) == 1
    assert features[0].title == "Test Feature"
    assert features[0].status == FeatureStatus.PENDING
    
    # Test status update
    feature.update_status(FeatureStatus.IN_PROGRESS, "Starting implementation")
    assert feature.status == FeatureStatus.IN_PROGRESS
    assert feature.implementation_notes == "Starting implementation"
    
    # Test rejection
    feature.update_status(FeatureStatus.REJECTED, "Not feasible")
    assert feature.status == FeatureStatus.REJECTED
    assert feature.rejection_reason == "Not feasible"
    
    # Test tag management
    feature.add_tag("priority")
    assert "priority" in feature.tags
    assert len(feature.tags) == 3  # test, feature, priority
    
    # Test related files
    feature.add_related_file("src/main.py")
    assert "src/main.py" in feature.related_files
    
    # Test duplicate prevention
    feature.add_tag("priority")  # Should not add duplicate
    assert len(feature.tags) == 3
    
    feature.add_related_file("src/main.py")  # Should not add duplicate
    assert len(feature.related_files) == 1


def test_feature_cli(monkeypatch):
    """Test feature request CLI commands."""
    data_store = MockDataStore()
    monkeypatch.setattr("src.main.get_data_store", lambda: data_store)
    
    runner = CliRunner()

    # Test feature addition
    result = runner.invoke(
        app,
        ["feature", "add"],
        input="New Feature\nA new test feature\nmedium\ntest,cli\n"
    )
    assert result.exit_code == 0
    assert "Feature request added successfully!" in result.stdout
    
    features = data_store.get_all(FeatureRequest)
    assert len(features) == 1
    assert features[0].title == "New Feature"
    
    # Test feature listing
    result = runner.invoke(app, ["feature", "list"])
    assert result.exit_code == 0
    assert "New Feature" in result.stdout
    assert "pending" in result.stdout.lower()
    
    # Test feature update
    feature_id = str(features[0].id)
    result = runner.invoke(
        app,
        ["feature", "update", "--feature-id", feature_id],
        input="Updated Feature\nUpdated description\nmedium\nin_progress\nImplementation started\ntest,cli,update\n"
    )
            assert result.exit_code == 0
    assert "Feature request updated successfully!" in result.stdout
    
    updated_feature = data_store.get_by_id(FeatureRequest, feature_id)
    assert updated_feature.title == "Updated Feature"
    assert updated_feature.status == FeatureStatus.IN_PROGRESS
    assert "Implementation started" in updated_feature.implementation_notes
    assert "update" in updated_feature.tags
    
    # Test feature deletion
    result = runner.invoke(app, ["feature", "delete", "--feature-id", feature_id])
    assert result.exit_code == 0
    assert "Feature request deleted successfully!" in result.stdout
    
    features = data_store.get_all(FeatureRequest)
    assert len(features) == 0 