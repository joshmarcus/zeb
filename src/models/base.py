from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    subtasks: List["Task"] = Field(default_factory=list)
    project_id: Optional[UUID] = None
    tags: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class Project(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    tasks: List[Task] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    tags: List[str] = Field(default_factory=list)


class JournalEntry(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    content: str
    mood: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    related_tasks: List[UUID] = Field(default_factory=list)
    reflection_type: str  # e.g., "morning_checkin", "evening_review", "procrastination", "anxiety", "reflection"


class CheckIn(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    type: str  # "morning" or "evening"
    priorities: List[str]
    reflections: List[str]
    tasks_completed: List[UUID]
    tasks_added: List[UUID]
    mood: Optional[str] = None
    notes: List[str] = Field(default_factory=list)


class FeatureStatus(str, Enum):
    """Status of a feature request."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class FeatureRequest(BaseModel):
    """Model for feature requests."""
    id: UUID = uuid4()
    title: str
    description: str
    status: FeatureStatus = FeatureStatus.PENDING
    priority: Priority
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    implementation_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    related_files: List[str] = []
    tags: List[str] = []

    def update_status(self, new_status: FeatureStatus, notes: Optional[str] = None):
        """Update the status and add implementation notes or rejection reason."""
        self.status = new_status
        self.updated_at = datetime.now()
        
        if new_status == FeatureStatus.REJECTED and notes:
            self.rejection_reason = notes
        elif notes:
            self.implementation_notes = notes

    def add_related_file(self, file_path: str):
        """Add a related file to the feature request."""
        if file_path not in self.related_files:
            self.related_files.append(file_path)
            self.updated_at = datetime.now()

    def add_tag(self, tag: str):
        """Add a tag to the feature request."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()


# Update forward references
Task.model_rebuild()
Project.model_rebuild() 