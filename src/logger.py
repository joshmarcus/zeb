import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid
from uuid import UUID

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class SessionLogger:
    def __init__(self, log_dir: str = "data/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_file = self.log_dir / "sessions.json"
        self.sessions: Dict[str, Dict] = {}
        self.current_session: Optional[str] = None
        self._load_sessions()

    def _load_sessions(self) -> None:
        """Load existing sessions from file."""
        if self.sessions_file.exists():
            self.sessions = json.loads(self.sessions_file.read_text())

    def _save_sessions(self) -> None:
        """Save sessions to file."""
        self.sessions_file.write_text(json.dumps(self.sessions, indent=2, cls=CustomJSONEncoder))

    def start_session(self, session_type: str) -> str:
        """Start a new session."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "type": session_type,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "interactions": []
        }
        self.current_session = session_id
        return session_id

    def log_interaction(self, session_id: str, interaction: Dict) -> None:
        """Log an interaction in a session."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        self.sessions[session_id]["interactions"].append({
            "timestamp": datetime.now().isoformat(),
            **interaction
        })
        self._save_sessions()

    def end_session(self, session_id: str) -> None:
        """End a session."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        self.sessions[session_id]["end_time"] = datetime.now().isoformat()
        if self.current_session == session_id:
            self.current_session = None
        self._save_sessions()

    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Get recent sessions."""
        return sorted(
            self.sessions.values(),
            key=lambda x: x["start_time"],
            reverse=True
        )[:limit]

    def get_conversation_history(self, days: int = 30, session_types: Optional[List[str]] = None) -> List[Dict]:
        """Get conversation history with full message content.
        
        Args:
            days: Number of days of history to include
            session_types: Optional filter for specific session types
            
        Returns:
            List of conversation sessions with full text
        """
        start_date = datetime.now() - timedelta(days=days)
        
        # Filter sessions by date and type
        filtered_sessions = []
        for session_id, session in self.sessions.items():
            if datetime.fromisoformat(session["start_time"]) >= start_date:
                if session_types is None or session["type"] in session_types:
                    # Add the session_id to the session data
                    session_data = {**session, "id": session_id}
                    filtered_sessions.append(session_data)
        
        # Sort sessions by start time (newest first)
        return sorted(
            filtered_sessions,
            key=lambda x: x["start_time"],
            reverse=True
        ) 