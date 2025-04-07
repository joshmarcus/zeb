import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..models.base import CheckIn, JournalEntry, Task
from ..storage.data_store import DataStore

class PromptBuilder:
    def __init__(self, data_store: DataStore, prompt_dir: str = "data/prompts"):
        self.data_store = data_store
        self.prompt_dir = Path(prompt_dir)
        self.prompt_dir.mkdir(parents=True, exist_ok=True)
        self.prompt_versions_file = self.prompt_dir / "versions.json"
        self._load_prompt_versions()

    def _load_prompt_versions(self) -> None:
        """Load or initialize prompt versions."""
        try:
            with open(self.prompt_dir / "versions.json", "r") as f:
                data = json.load(f)
                # Handle old format
                if "system" in data:
                    self.prompt_versions = {
                        1: {
                            "prompt": data["system"]["versions"]["1.0"],
                            "timestamp": datetime.now().isoformat(),
                            "changes": {}
                        }
                    }
                else:
                    self.prompt_versions = {int(k): v for k, v in data.items()}
        except FileNotFoundError:
            # Initialize with default prompt
            self.prompt_versions = {
                1: {
                    "prompt": self._get_default_system_prompt(),
                    "timestamp": datetime.now().isoformat(),
                    "changes": {}
                }
            }
        
        # Save in new format
        self._save_prompt_versions()

    def _save_prompt_versions(self) -> None:
        """Save prompt versions to disk."""
        os.makedirs(self.prompt_dir, exist_ok=True)
        with open(self.prompt_dir / "versions.json", "w") as f:
            json.dump(self.prompt_versions, f, indent=2)

    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt."""
        return """You are a productivity coach helping users stay focused and achieve their goals.
Your role is to:
1. Provide actionable insights based on the user's tasks, check-ins, and journal entries
2. Help identify patterns in productivity and procrastination
3. Suggest improvements to their workflow
4. Offer encouragement and accountability
5. Help break down complex tasks into manageable steps

Be concise, practical, and empathetic in your responses."""

    def build_morning_prompt(self, days: int = 7) -> str:
        """Build a prompt for morning coaching."""
        context = self._get_context(days)
        return f"""Based on the following context, provide morning coaching to help set up for a productive day:

{context}

Focus on:
1. Reviewing priorities from yesterday
2. Setting clear goals for today
3. Identifying potential challenges
4. Suggesting specific actions to maintain focus

Keep the response concise and actionable."""

    def build_evening_prompt(self, days: int = 7) -> str:
        """Build a prompt for evening coaching."""
        context = self._get_context(days)
        return f"""Based on the following context, provide evening coaching to reflect on the day:

{context}

Focus on:
1. Celebrating accomplishments
2. Identifying areas for improvement
3. Suggesting adjustments for tomorrow
4. Providing encouragement for continued progress

Keep the response concise and supportive."""

    def build_procrastination_prompt(self, journal_entry: JournalEntry) -> str:
        """Build a prompt for analyzing procrastination."""
        return f"""Analyze this procrastination journal entry and provide insights:

Entry: {journal_entry.content}
Mood: {journal_entry.mood}
Related Tasks: {[str(t) for t in journal_entry.related_tasks]}

Focus on:
1. Identifying triggers and patterns
2. Suggesting practical coping strategies
3. Breaking down overwhelming tasks
4. Providing encouragement to move forward

Keep the response concise and actionable."""

    def build_task_breakdown_prompt(self, task: Task) -> str:
        """Build a prompt for task breakdown."""
        return f"""Break down this task into smaller, manageable subtasks:

Task: {task.title}
Description: {task.description}
Priority: {task.priority}

Provide 3-5 specific, actionable subtasks that would help complete this task.
Each subtask should be clear and achievable within a short time frame."""

    def _get_context(self, days: int = 7) -> str:
        """Gather context for prompts."""
        now = datetime.now()
        context = []
        
        # Get recent check-ins
        checkins = self.data_store.get_checkins_by_date(now)
        if checkins:
            context.append("Recent Check-ins:")
            for checkin in checkins:
                context.append(f"- {checkin.type} check-in: {', '.join(checkin.priorities)}")
        
        # Get recent journal entries
        entries = self.data_store.get_journal_entries_by_date(now)
        if entries:
            context.append("\nRecent Journal Entries:")
            for entry in entries:
                context.append(f"- {entry.reflection_type}: {entry.content[:100]}...")
        
        # Get active tasks
        tasks = self.data_store.get_all(Task)
        active_tasks = [t for t in tasks if t.status != "done"]
        if active_tasks:
            context.append("\nActive Tasks:")
            for task in active_tasks:
                context.append(f"- {task.title} ({task.status})")
        
        return "\n".join(context)

    def update_system_prompt(self, changes: Dict) -> None:
        """Update the system prompt based on suggested changes."""
        current_prompt = self.get_current_system_prompt()
        new_prompt = current_prompt
        
        # Apply changes based on the improvement suggestions
        for prompt_type, improvements in changes.items():
            if prompt_type not in new_prompt:
                continue
                
            for issue, changes in improvements["suggested_changes"].items():
                # Add new prompt elements
                for addition in changes["add"]:
                    if addition not in new_prompt:
                        new_prompt += f"\n{addition}"
                
                # Remove outdated elements
                for removal in changes["remove"]:
                    new_prompt = new_prompt.replace(removal, "")
        
        # Create new version
        version = max(self.prompt_versions.keys()) + 1
        self.prompt_versions[version] = {
            "prompt": new_prompt,
            "timestamp": datetime.now().isoformat(),
            "changes": changes
        }
        
        # Save updated versions
        self._save_prompt_versions()

    def get_prompt_effectiveness(self, prompt_type: str) -> Dict:
        """Get effectiveness metrics for a specific prompt type."""
        if not self.prompt_versions:
            return {"score": 1.0, "history": []}
            
        # Get version history for the prompt type
        history = []
        for version, data in self.prompt_versions.items():
            if "changes" in data and prompt_type in data["changes"]:
                history.append({
                    "version": version,
                    "timestamp": data["timestamp"],
                    "score": data["changes"][prompt_type]["current_score"],
                    "issues": data["changes"][prompt_type]["issues"]
                })
        
        # Calculate current effectiveness
        current_score = 1.0
        if history:
            current_score = history[-1]["score"]
        
        return {
            "score": current_score,
            "history": history
        }

    def rollback_prompt(self, version: int) -> None:
        """Rollback to a previous prompt version."""
        if version not in self.prompt_versions:
            raise ValueError(f"Version {version} does not exist")
            
        # Create new version with rolled back content
        new_version = max(self.prompt_versions.keys()) + 1
        self.prompt_versions[new_version] = {
            "prompt": self.prompt_versions[version]["prompt"],
            "timestamp": datetime.now().isoformat(),
            "changes": {
                "type": "rollback",
                "from_version": version
            }
        }
        
        # Save updated versions
        self._save_prompt_versions()

    def get_current_system_prompt(self) -> str:
        """Get the current system prompt."""
        current_version = max(self.prompt_versions.keys())
        return self.prompt_versions[current_version]["prompt"] 