from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import json

from .models.base import Task, JournalEntry, CheckIn
from .storage.data_store import DataStore

class ContextManager:
    def __init__(self, data_store: DataStore, context_dir: str = "data/context"):
        self.data_store = data_store
        self.context_dir = Path(context_dir)
        self.context_dir.mkdir(parents=True, exist_ok=True)
        self.context_file = self.context_dir / "context.json"
        self._load_context()

    def _load_context(self) -> None:
        """Load or initialize context."""
        if self.context_file.exists():
            self.context = json.loads(self.context_file.read_text())
        else:
            self.context = {
                "user": {
                    "goals": [],
                    "preferences": {},
                    "patterns": {}
                },
                "assistant": {
                    "memory": [],
                    "adaptations": {}
                }
            }
            self._save_context()

    def _save_context(self) -> None:
        """Save context to file."""
        self.context_file.write_text(json.dumps(self.context, indent=2))

    def update_user_goals(self, goals: List[str]) -> None:
        """Update user's goals."""
        self.context["user"]["goals"] = goals
        self._save_context()

    def update_user_preferences(self, preferences: Dict) -> None:
        """Update user's preferences."""
        self.context["user"]["preferences"].update(preferences)
        self._save_context()

    def update_user_patterns(self, patterns: Dict) -> None:
        """Update user's productivity patterns."""
        self.context["user"]["patterns"].update(patterns)
        self._save_context()

    def add_to_assistant_memory(self, memory_item: Dict) -> None:
        """Add an item to assistant's memory."""
        self.context["assistant"]["memory"].append({
            "timestamp": datetime.now().isoformat(),
            **memory_item
        })
        # Keep only last 100 memory items
        self.context["assistant"]["memory"] = self.context["assistant"]["memory"][-100:]
        self._save_context()

    def update_assistant_adaptations(self, adaptations: Dict) -> None:
        """Update assistant's adaptations based on user interactions."""
        self.context["assistant"]["adaptations"].update(adaptations)
        self._save_context()

    def track_conversation_topic(self, topic: str, importance: int = 1) -> None:
        """Track a conversation topic to understand user interests.
        
        Args:
            topic: The topic being discussed
            importance: Importance level (1-10)
        """
        if "conversation_topics" not in self.context["user"]:
            self.context["user"]["conversation_topics"] = {}
            
        if topic in self.context["user"]["conversation_topics"]:
            self.context["user"]["conversation_topics"][topic] += importance
        else:
            self.context["user"]["conversation_topics"][topic] = importance
            
        # Ensure we only keep the top 20 topics
        sorted_topics = sorted(
            self.context["user"]["conversation_topics"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:20]
        
        self.context["user"]["conversation_topics"] = dict(sorted_topics)
        self._save_context()
        
    def store_emotional_state(self, emotion: str, intensity: int = 5, trigger: Optional[str] = None) -> None:
        """Store information about the user's emotional state.
        
        Args:
            emotion: The detected emotion (e.g., 'anxious', 'motivated')
            intensity: Intensity level (1-10)
            trigger: Optional trigger for the emotion
        """
        if "emotional_states" not in self.context["user"]:
            self.context["user"]["emotional_states"] = []
            
        self.context["user"]["emotional_states"].append({
            "timestamp": datetime.now().isoformat(),
            "emotion": emotion,
            "intensity": intensity,
            "trigger": trigger
        })
        
        # Keep only the 50 most recent emotional states
        self.context["user"]["emotional_states"] = self.context["user"]["emotional_states"][-50:]
        self._save_context()
        
    def get_recent_context(self, days: int = 7) -> Dict:
        """Get recent context for the assistant."""
        now = datetime.now()
        start_date = now - timedelta(days=days)
        
        # Get basic context items
        context = {
            "tasks": self._get_recent_tasks(start_date),
            "journal_entries": self._get_recent_journal_entries(start_date),
            "check_ins": self._get_recent_check_ins(start_date),
            "user_goals": self.context["user"]["goals"],
            "user_patterns": self.context["user"]["patterns"],
            "assistant_memory": self._get_relevant_memory(start_date)
        }
        
        # Add conversation topics if available
        if "conversation_topics" in self.context["user"]:
            context["conversation_topics"] = self.context["user"]["conversation_topics"]
            
        # Add emotional states if available
        if "emotional_states" in self.context["user"]:
            # Only include emotional states from within the time period
            recent_emotions = [
                e for e in self.context["user"]["emotional_states"]
                if datetime.fromisoformat(e["timestamp"]) >= start_date
            ]
            
            if recent_emotions:
                context["emotional_states"] = recent_emotions
                
                # Calculate current emotional trend
                if len(recent_emotions) >= 3:
                    emotions = [e["emotion"] for e in recent_emotions[-3:]]
                    context["emotional_trend"] = ", ".join(emotions)
        
        return context

    def _get_recent_tasks(self, start_date: datetime) -> List[Dict]:
        """Get recent tasks."""
        tasks = self.data_store.get_all(Task)
        return [
            {
                "id": str(task.id),
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "created_at": task.created_at.isoformat()
            }
            for task in tasks
            if task.created_at >= start_date
        ]

    def _get_recent_journal_entries(self, start_date: datetime) -> List[Dict]:
        """Get recent journal entries."""
        entries = self.data_store.get_all(JournalEntry)
        return [
            {
                "id": str(entry.id),
                "type": entry.reflection_type,
                "content": entry.content,
                "mood": entry.mood,
                "created_at": entry.timestamp.isoformat()
            }
            for entry in entries
            if entry.timestamp >= start_date
        ]

    def _get_recent_check_ins(self, start_date: datetime) -> List[Dict]:
        """Get recent check-ins."""
        check_ins = self.data_store.get_all(CheckIn)
        return [
            {
                "id": str(check_in.id),
                "type": check_in.type,
                "priorities": check_in.priorities,
                "created_at": check_in.timestamp.isoformat()
            }
            for check_in in check_ins
            if check_in.timestamp >= start_date
        ]

    def _get_relevant_memory(self, start_date: datetime) -> List[Dict]:
        """Get relevant assistant memory items."""
        return [
            memory_item
            for memory_item in self.context["assistant"]["memory"]
            if datetime.fromisoformat(memory_item["timestamp"]) >= start_date
        ]

    def analyze_productivity_patterns(self) -> Dict:
        """Analyze productivity patterns from recent data."""
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        
        tasks = self._get_recent_tasks(thirty_days_ago)
        journal_entries = self._get_recent_journal_entries(thirty_days_ago)
        check_ins = self._get_recent_check_ins(thirty_days_ago)
        
        patterns = {
            "task_completion_rate": self._calculate_task_completion_rate(tasks),
            "common_procrastination_triggers": self._identify_procrastination_triggers(journal_entries),
            "productive_times": self._identify_productive_times(check_ins, tasks),
            "goal_progress": self._track_goal_progress(tasks, journal_entries)
        }
        
        self.update_user_patterns(patterns)
        return patterns

    def _calculate_task_completion_rate(self, tasks: List[Dict]) -> float:
        """Calculate task completion rate."""
        if not tasks:
            return 0.0
        completed = sum(1 for task in tasks if task["status"] == "done")
        return completed / len(tasks)

    def _identify_procrastination_triggers(self, journal_entries: List[Dict]) -> List[str]:
        """Identify common procrastination triggers from journal entries."""
        triggers = []
        for entry in journal_entries:
            if entry["type"] == "procrastination":
                # Simple keyword-based trigger identification
                content = entry["content"].lower()
                if "overwhelmed" in content:
                    triggers.append("task_overwhelm")
                if "distracted" in content:
                    triggers.append("distractions")
                if "tired" in content or "exhausted" in content:
                    triggers.append("fatigue")
        return list(set(triggers))

    def _identify_productive_times(self, check_ins: List[Dict], tasks: List[Dict]) -> Dict:
        """Identify most productive times of day."""
        productive_hours = {}
        for check_in in check_ins:
            hour = datetime.fromisoformat(check_in["created_at"]).hour
            if hour not in productive_hours:
                productive_hours[hour] = 0
            productive_hours[hour] += 1
        
        return {
            "most_productive_hours": sorted(
                productive_hours.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
        }

    def _track_goal_progress(self, tasks: List[Dict], journal_entries: List[Dict]) -> Dict:
        """Track progress towards user goals."""
        goal_progress = {}
        for goal in self.context["user"]["goals"]:
            relevant_tasks = [
                task for task in tasks
                if goal.lower() in task["title"].lower()
            ]
            relevant_entries = [
                entry for entry in journal_entries
                if goal.lower() in entry["content"].lower()
            ]
            
            goal_progress[goal] = {
                "completed_tasks": sum(1 for task in relevant_tasks if task["status"] == "done"),
                "total_tasks": len(relevant_tasks),
                "journal_mentions": len(relevant_entries)
            }
        
        return goal_progress 