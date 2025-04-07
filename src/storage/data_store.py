import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type, TypeVar, Union, Any
from uuid import UUID

from ..models.base import CheckIn, JournalEntry, Project, Task, FeatureRequest

T = TypeVar("T", Task, Project, JournalEntry, CheckIn, FeatureRequest)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class DataStore:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize data files
        self.tasks_file = self.data_dir / "tasks.json"
        self.projects_file = self.data_dir / "projects.json"
        self.journal_file = self.data_dir / "journal.json"
        self.checkins_file = self.data_dir / "checkins.json"
        self.features_file = self.data_dir / "features.json"
        
        # Create files if they don't exist
        for file in [self.tasks_file, self.projects_file, self.journal_file, self.checkins_file, self.features_file]:
            if not file.exists():
                file.write_text("[]")

    def _load_data(self, file_path: Path) -> List[Dict]:
        """Load data from a JSON file."""
        return json.loads(file_path.read_text())

    def _save_data(self, file_path: Path, data: List[Dict]) -> None:
        """Save data to a JSON file."""
        file_path.write_text(json.dumps(data, cls=CustomJSONEncoder, indent=2))

    def _get_file_for_type(self, model_type: Type[T]) -> Path:
        """Get the appropriate file path for a given model type."""
        if model_type == Task:
            return self.tasks_file
        elif model_type == Project:
            return self.projects_file
        elif model_type == JournalEntry:
            return self.journal_file
        elif model_type == CheckIn:
            return self.checkins_file
        elif model_type == FeatureRequest:
            return self.features_file
        raise ValueError(f"Unknown model type: {model_type}")

    def save(self, item: T) -> None:
        """Save a single item to the appropriate file."""
        file_path = self._get_file_for_type(type(item))
        data = self._load_data(file_path)
        
        # Convert item to dict
        item_dict = item.model_dump()
        
        # Update existing item or append new one
        for i, existing in enumerate(data):
            if existing["id"] == str(item_dict["id"]):
                data[i] = item_dict
                break
        else:
            data.append(item_dict)
            
        self._save_data(file_path, data)

    def get_by_id(self, model_type: Type[T], item_id: Union[str, UUID]) -> Optional[T]:
        """Retrieve an item by its ID."""
        file_path = self._get_file_for_type(model_type)
        data = self._load_data(file_path)
        
        item_id = str(item_id)
        for item in data:
            if item["id"] == item_id:
                return model_type.model_validate(item)
        return None

    def get_all(self, model_type: Type[T]) -> List[T]:
        """Retrieve all items of a given type."""
        file_path = self._get_file_for_type(model_type)
        data = self._load_data(file_path)
        return [model_type.model_validate(item) for item in data]

    def delete(self, model_type: Type[T], item_id: Union[str, UUID]) -> bool:
        """Delete an item by its ID."""
        file_path = self._get_file_for_type(model_type)
        data = self._load_data(file_path)
        
        item_id = str(item_id)
        for i, item in enumerate(data):
            if item["id"] == item_id:
                data.pop(i)
                self._save_data(file_path, data)
                return True
        return False

    def get_tasks_by_project(self, project_id: Union[str, UUID]) -> List[Task]:
        """Get all tasks associated with a project."""
        tasks = self.get_all(Task)
        project_id = str(project_id)
        return [task for task in tasks if task.project_id and str(task.project_id) == project_id]

    def get_journal_entries_by_date(self, date: datetime) -> List[JournalEntry]:
        """Get all journal entries for a specific date."""
        entries = self.get_all(JournalEntry)
        return [
            entry for entry in entries
            if entry.timestamp.date() == date.date()
        ]

    def get_checkins_by_date(self, date: datetime) -> List[CheckIn]:
        """Get all check-ins for a specific date."""
        checkins = self.get_all(CheckIn)
        return [
            checkin for checkin in checkins
            if checkin.timestamp.date() == date.date()
        ] 