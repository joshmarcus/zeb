import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import json
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI

from ..models.base import CheckIn, JournalEntry, Task
from ..storage.data_store import DataStore
from .prompt_builder import PromptBuilder

load_dotenv()

class ProductivityCoach:
    def __init__(self, data_store: DataStore):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.data_store = data_store
        self.system_prompt = self._load_system_prompt()
        self.context_manager = None  # Will be set in main.py
        self.coaching_style = {
            "tone": "assertive",  # assertive, supportive, strict
            "detail_level": "balanced",  # minimal, balanced, detailed
            "focus_areas": ["task_completion", "time_management", "goal_tracking"],
            "check_in_frequency": "twice_daily",  # twice_daily, thrice_daily, custom
            "reminder_intensity": "moderate"  # gentle, moderate, strong
        }
        self.last_reflection = None
        self.adaptation_history = []

    def _load_system_prompt(self) -> str:
        """Load or initialize the system prompt for the coach."""
        # TODO: Implement prompt versioning and storage
        return """You are a productivity coach helping users stay focused and achieve their goals.
Your role is to:
1. Provide actionable insights based on the user's tasks, check-ins, and journal entries
2. Help identify patterns in productivity and procrastination
3. Suggest improvements to their workflow
4. Offer encouragement and accountability
5. Help break down complex tasks into manageable steps

Be concise, practical, and empathetic in your responses."""

    def _get_context(self, days: int = 7) -> str:
        """Gather recent context for the coach."""
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

    def get_morning_coaching(self, prompt: str = None) -> str:
        """Generate morning coaching insights and suggestions."""
        if prompt is None:
            context = self._get_context()
            prompt = f"""Based on the following context, provide morning coaching to help set up for a productive day:

{context}

Focus on:
1. Reviewing priorities from yesterday
2. Setting clear goals for today
3. Identifying potential challenges
4. Suggesting specific actions to maintain focus

Keep the response concise and actionable."""

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content

    def get_evening_coaching(self, prompt: str = None) -> str:
        """Generate evening coaching insights and reflections."""
        if prompt is None:
            context = self._get_context()
            prompt = f"""Based on the following context, provide evening coaching to reflect on the day:

{context}

Focus on:
1. Celebrating accomplishments
2. Identifying areas for improvement
3. Suggesting adjustments for tomorrow
4. Providing encouragement for continued progress

Keep the response concise and supportive."""

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content

    def analyze_procrastination(self, journal_entry: JournalEntry) -> str:
        """Analyze a procrastination journal entry and provide insights."""
        prompt = f"""Analyze this procrastination journal entry and provide insights:

Entry: {journal_entry.content}
Mood: {journal_entry.mood}
Related Tasks: {[str(t) for t in journal_entry.related_tasks]}

Focus on:
1. Identifying triggers and patterns
2. Suggesting practical coping strategies
3. Breaking down overwhelming tasks
4. Providing encouragement to move forward

Keep the response concise and actionable."""

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content

    def suggest_task_breakdown(self, task: Task) -> List[str]:
        """Suggest a breakdown for a complex task."""
        prompt = f"""Break down this task into smaller, manageable subtasks:

Task: {task.title}
Description: {task.description}
Priority: {task.priority}

Provide 3-5 specific, actionable subtasks that would help complete this task.
Each subtask should be clear and achievable within a short time frame."""

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        # Parse the response into a list of subtasks
        subtasks = [
            line.strip("- ").strip()
            for line in response.choices[0].message.content.split("\n")
            if line.strip().startswith("-")
        ]
        
        return subtasks

    def expand_feature_request(self, description: str) -> Dict:
        """Expand a natural language feature request into a structured format."""
        try:
            print("\nProcessing feature request...")
            prompt = f"""Given this natural language feature request:
"{description}"

Please analyze this request and provide a structured response in the following JSON format:
{{
    "title": "string",
    "description": "string",
    "priority": "low|medium|high",
    "tags": ["string"]
}}

Make sure the description is comprehensive but clear."""

            print("\nSending request to OpenAI API...")
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            print("\nResponse received from OpenAI API")
            content = response.choices[0].message.content
            print(f"Raw response: {content}")
            
            try:
                result = json.loads(content)
                print("\nSuccessfully parsed JSON response")
                return result
            except json.JSONDecodeError as e:
                print(f"\nError decoding JSON response: {e}")
                print("Using fallback response format")
                return {
                    "title": description[:100],
                    "description": description,
                    "priority": "medium",
                    "tags": []
                }
                
        except Exception as e:
            print(f"\nError in expand_feature_request: {type(e).__name__}: {str(e)}")
            print("Using fallback response format")
            return {
                "title": description[:100],
                "description": description,
                "priority": "medium",
                "tags": []
            }

    def update_system_prompt(self, feedback: str) -> None:
        """Update the system prompt based on user feedback."""
        # TODO: Implement prompt versioning and storage
        prompt = f"""Based on this feedback, suggest improvements to the coaching system prompt:

Feedback: {feedback}

Current prompt:
{self.system_prompt}

Provide an updated version of the system prompt that addresses the feedback while maintaining the core coaching objectives."""

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a prompt engineering expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        self.system_prompt = response.choices[0].message.content

    def reflect_on_coaching(self) -> Dict:
        """Analyze recent interactions and suggest coaching adaptations."""
        recent_context = self.context_manager.get_recent_context(days=7)
        
        # Analyze task completion patterns
        task_completion_rate = self._analyze_task_completion(recent_context["tasks"])
        
        # Analyze user engagement
        engagement_patterns = self._analyze_user_engagement(
            recent_context["check_ins"],
            recent_context["journal_entries"]
        )
        
        # Analyze mood and stress patterns
        mood_patterns = self._analyze_mood_patterns(recent_context["journal_entries"])
        
        # Generate coaching adaptations
        adaptations = self._generate_coaching_adaptations(
            task_completion_rate,
            engagement_patterns,
            mood_patterns
        )
        
        # Analyze and propose prompt changes
        prompt_changes = self._analyze_prompt_effectiveness(recent_context)
        if prompt_changes:
            adaptations["prompt_changes"] = prompt_changes
        
        reflection = {
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "task_completion_rate": task_completion_rate,
                "engagement_score": engagement_patterns["engagement_score"],
                "mood_trend": mood_patterns["trend"]
            },
            "proposed_adaptations": adaptations
        }
        
        self.last_reflection = reflection
        self.adaptation_history.append(reflection)
        
        return reflection

    def _analyze_task_completion(self, tasks: List[Dict]) -> float:
        """Analyze task completion patterns."""
        if not tasks:
            return 0.0
        completed = sum(1 for task in tasks if task["status"] == "done")
        return completed / len(tasks)

    def _analyze_user_engagement(self, check_ins: List[Dict], journal_entries: List[Dict]) -> Dict:
        """Analyze user engagement with the system."""
        expected_check_ins = 14  # 2 per day for 7 days
        actual_check_ins = len(check_ins)
        journal_frequency = len(journal_entries) / 7  # avg entries per day
        
        engagement_score = (actual_check_ins / expected_check_ins) * 0.7 + (min(journal_frequency, 1) * 0.3)
        
        return {
            "engagement_score": engagement_score,
            "check_in_adherence": actual_check_ins / expected_check_ins,
            "journal_frequency": journal_frequency
        }

    def _analyze_mood_patterns(self, journal_entries: List[Dict]) -> Dict:
        """Analyze mood patterns from journal entries."""
        if not journal_entries:
            return {"trend": "neutral", "stress_level": "moderate"}
        
        moods = [entry.get("mood", "neutral") for entry in journal_entries]
        stress_indicators = sum(
            1 for entry in journal_entries
            if any(word in entry["content"].lower() 
                  for word in ["stress", "overwhelm", "anxiety", "tired"])
        )
        
        # Simple mood trend analysis
        positive_moods = sum(1 for mood in moods if mood in ["happy", "productive", "energetic"])
        negative_moods = sum(1 for mood in moods if mood in ["stressed", "frustrated", "exhausted"])
        
        trend = "neutral"
        if positive_moods > len(moods) * 0.6:
            trend = "positive"
        elif negative_moods > len(moods) * 0.4:
            trend = "negative"
            
        stress_level = "low"
        if stress_indicators > len(journal_entries) * 0.3:
            stress_level = "moderate"
        if stress_indicators > len(journal_entries) * 0.6:
            stress_level = "high"
            
        return {
            "trend": trend,
            "stress_level": stress_level
        }

    def _generate_coaching_adaptations(
        self,
        task_completion_rate: float,
        engagement_patterns: Dict,
        mood_patterns: Dict
    ) -> Dict:
        """Generate coaching style adaptations based on analysis."""
        adaptations = {}
        
        # Adjust tone based on mood and stress
        if mood_patterns["stress_level"] == "high":
            adaptations["tone"] = "supportive"
        elif task_completion_rate < 0.5 and mood_patterns["trend"] != "negative":
            adaptations["tone"] = "strict"
            
        # Adjust detail level based on engagement
        if engagement_patterns["engagement_score"] < 0.5:
            adaptations["detail_level"] = "minimal"
        elif engagement_patterns["engagement_score"] > 0.8:
            adaptations["detail_level"] = "detailed"
            
        # Adjust focus areas
        focus_areas = []
        if task_completion_rate < 0.7:
            focus_areas.append("task_completion")
        if engagement_patterns["check_in_adherence"] < 0.7:
            focus_areas.append("consistency")
        if mood_patterns["stress_level"] in ["moderate", "high"]:
            focus_areas.append("stress_management")
            
        if focus_areas:
            adaptations["focus_areas"] = focus_areas
            
        # Adjust reminder intensity
        if engagement_patterns["check_in_adherence"] < 0.5:
            adaptations["reminder_intensity"] = "strong"
        elif engagement_patterns["check_in_adherence"] > 0.9:
            adaptations["reminder_intensity"] = "gentle"
            
        return adaptations

    def _analyze_prompt_effectiveness(self, context: Dict) -> Dict:
        """Analyze the effectiveness of prompts based on user interactions."""
        effectiveness = {}
        
        # Analyze morning prompt effectiveness
        morning_check_ins = [
            c for c in context.get("check_ins", [])
            if c["type"] == "morning"
        ]
        if morning_check_ins:
            score = 1.0
            issues = []
            
            # Check for task clarity
            unclear_tasks = sum(
                1 for c in morning_check_ins
                if any("unclear" in str(p).lower() or "need to" in str(p).lower() 
                      for p in c.get("priorities", []))
            )
            if unclear_tasks / len(morning_check_ins) > 0.3:
                score -= 0.2
                issues.append("Tasks often lack clarity")
            
            # Check for priority setting
            no_priorities = sum(
                1 for c in morning_check_ins
                if not c.get("priorities")
            )
            if no_priorities / len(morning_check_ins) > 0.2:
                score -= 0.2
                issues.append("Priorities not consistently set")
                
            effectiveness["morning_prompt"] = {
                "current_score": max(0.0, score),
                "issues": issues
            }
        
        # Analyze evening prompt effectiveness
        evening_check_ins = [
            c for c in context.get("check_ins", [])
            if c["type"] == "evening"
        ]
        if evening_check_ins:
            score = 1.0
            issues = []
            
            # Check for reflection depth
            shallow_reflections = sum(
                1 for c in evening_check_ins
                if len(c.get("priorities", [])) < 2
            )
            if shallow_reflections / len(evening_check_ins) > 0.3:
                score -= 0.2
                issues.append("Reflections lack depth")
            
            # Check for progress tracking
            no_progress = sum(
                1 for c in evening_check_ins
                if not any("completed" in str(v).lower() 
                          for v in c.values())
            )
            if no_progress / len(evening_check_ins) > 0.2:
                score -= 0.2
                issues.append("Progress not consistently tracked")
                
            effectiveness["evening_prompt"] = {
                "current_score": max(0.0, score),
                "issues": issues
            }
        
        # Analyze task breakdown effectiveness
        tasks = context.get("tasks", [])
        if tasks:
            score = 1.0
            issues = []
            
            # Check for task completion after breakdown
            incomplete_breakdowns = sum(
                1 for task in tasks
                if task.get("status") != "done" and len(task.get("subtasks", [])) > 0
            )
            if incomplete_breakdowns / len(tasks) > 0.4:
                score -= 0.3
                issues.append("Task breakdowns not leading to completion")
            
            # Check for subtask quality
            vague_subtasks = sum(
                1 for task in tasks
                if any("todo" in str(subtask).lower() or "need to" in str(subtask).lower()
                      for subtask in task.get("subtasks", []))
            )
            if vague_subtasks / len(tasks) > 0.3:
                score -= 0.2
                issues.append("Subtasks often lack specificity")
                
            effectiveness["task_breakdown_prompt"] = {
                "current_score": max(0.0, score),
                "issues": issues
            }
        
        return effectiveness

    def _generate_prompt_improvements(self, prompt_type: str, issues: List[str]) -> Dict:
        """Generate specific improvements for a prompt type."""
        improvements = {
            "morning_prompt": {
                "task_clarity": {
                    "add": [
                        "Ask for specific, measurable outcomes for each task",
                        "Request time estimates for each priority",
                        "Prompt for potential blockers upfront"
                    ],
                    "remove": [
                        "Generic task descriptions",
                        "Vague priority statements"
                    ]
                },
                "priority_setting": {
                    "add": [
                        "Force ranking of priorities (1-3)",
                        "Ask for commitment level to each priority",
                        "Request specific time slots for high-priority items"
                    ],
                    "remove": [
                        "Optional priority setting",
                        "Unranked task lists"
                    ]
                }
            },
            "evening_prompt": {
                "reflection_depth": {
                    "add": [
                        "Ask for specific challenges faced",
                        "Request quantitative progress metrics",
                        "Prompt for learning moments"
                    ],
                    "remove": [
                        "Yes/no completion questions",
                        "Generic progress updates"
                    ]
                },
                "progress_tracking": {
                    "add": [
                        "Time spent on each priority",
                        "Specific obstacles encountered",
                        "Adjustments made during the day"
                    ],
                    "remove": [
                        "Binary completion status",
                        "Missing progress details"
                    ]
                }
            },
            "task_breakdown_prompt": {
                "completion_focus": {
                    "add": [
                        "Request estimated completion time for each subtask",
                        "Ask for dependencies between subtasks",
                        "Prompt for potential blockers"
                    ],
                    "remove": [
                        "Open-ended subtask lists",
                        "Missing time estimates"
                    ]
                },
                "subtask_quality": {
                    "add": [
                        "Require action verbs in subtasks",
                        "Ask for specific outcomes",
                        "Request measurable completion criteria"
                    ],
                    "remove": [
                        "Vague subtask descriptions",
                        "Missing completion criteria"
                    ]
                }
            }
        }
        
        return {
            issue: improvements[prompt_type][issue]
            for issue in issues
            if issue in improvements[prompt_type]
        }

    def apply_adaptations(self, adaptations: Dict) -> None:
        """Apply the proposed coaching adaptations."""
        self.coaching_style.update(adaptations)
        
        # Apply prompt changes if present
        if "prompt_changes" in adaptations:
            for prompt_type, changes in adaptations["prompt_changes"].items():
                self.context_manager.add_to_assistant_memory({
                    "type": "prompt_adaptation",
                    "prompt_type": prompt_type,
                    "changes": changes,
                    "timestamp": datetime.now().isoformat()
                })
        
        # Update context with new adaptations
        self.context_manager.update_assistant_adaptations({
            "timestamp": datetime.now().isoformat(),
            "coaching_style": self.coaching_style,
            "reason": "Automated adaptation based on user patterns"
        })

    def get_coaching_context(self) -> Dict:
        """Get current coaching context for the assistant."""
        return {
            "coaching_style": self.coaching_style,
            "last_reflection": self.last_reflection,
            "adaptation_history": self.adaptation_history[-5:]  # Last 5 adaptations
        }

    def generate_chat_response(self, user_input, context=None, chat_history=None) -> str:
        """Generate a response to the user's input in a chat conversation.
        
        Args:
            user_input: The user's latest message or a system prompt describing the desired response.
            context: Optional recent context about the user's tasks, entries, etc.
            chat_history: Optional list of previous messages in the conversation.
            
        Returns:
            A response from the coach.
        """
        if context is None:
            context = self._get_context()
            
        if chat_history is None:
            chat_history = []
            
        # Create the chat prompt
        system_content = f"""{self.system_prompt}

You are engaging in a chat conversation with the user. Be conversational, friendly, and proactive.
Ask clarifying questions when needed, and provide actionable advice.

Here's recent context about the user's tasks, journal entries, and activities:
{context}

Remember to:
1. Be empathetic and supportive, especially with emotional challenges
2. Keep responses concise (2-3 paragraphs max)
3. Ask probing questions to understand deeper issues
4. Suggest concrete next steps or actions when appropriate
5. Follow up on previously discussed topics
"""

        # Create messages from chat history
        messages = [{"role": "system", "content": system_content}]
        for msg in chat_history[-10:]:  # Include up to 10 most recent messages
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        # If user_input is not in the chat history (system directive), add it
        if not chat_history or chat_history[-1]["role"] != "user" or chat_history[-1]["content"] != user_input:
            if not user_input.startswith("The user"):  # Avoid adding system directives as user messages
                messages.append({"role": "user", "content": user_input})
            else:
                # This is a system directive, add as a system message
                messages.append({"role": "system", "content": user_input})
                
        # Generate response
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating chat response: {e}")
            return "I'm having trouble processing that right now. Could you try rephrasing or ask something else?"
            
    def extract_task_details(self, task_description, context=None) -> dict:
        """Extract structured task details from a natural language description.
        
        Args:
            task_description: The user's description of the task.
            context: Optional recent context about the user's tasks, entries, etc.
            
        Returns:
            A dictionary with task details (title, description, priority, due_date).
        """
        if context is None:
            context = self._get_context(days=7)
            
        prompt = f"""Extract structured task details from this description:

Task Description: {task_description}

Based on this context of the user's existing tasks and priorities:
{context}

Extract the following information in JSON format:
{{
  "title": "A clear, concise title (max 50 chars)",
  "description": "Detailed description of what needs to be done",
  "priority": "low|medium|high|urgent",
  "due_date": "YYYY-MM-DD (if mentioned, otherwise null)"
}}

If any information is missing, make a reasonable inference based on context. For title, provide a concise summary of the task."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            response_text = response.choices[0].message.content
            
            # Extract JSON from response
            try:
                import json
                import re
                
                # Try to find JSON in the response
                json_match = re.search(r'({.*?})', response_text.replace('\n', ' '), re.DOTALL)
                if json_match:
                    task_details = json.loads(json_match.group(1))
                    return task_details
                else:
                    # Parse the response manually
                    task_details = {}
                    if "title" in response_text:
                        title_match = re.search(r'"title":\s*"([^"]+)"', response_text)
                        if title_match:
                            task_details["title"] = title_match.group(1)
                    
                    if "description" in response_text:
                        desc_match = re.search(r'"description":\s*"([^"]+)"', response_text)
                        if desc_match:
                            task_details["description"] = desc_match.group(1)
                    
                    if "priority" in response_text:
                        priority_match = re.search(r'"priority":\s*"([^"]+)"', response_text)
                        if priority_match:
                            task_details["priority"] = priority_match.group(1)
                    
                    if "due_date" in response_text:
                        date_match = re.search(r'"due_date":\s*"([^"]+)"', response_text)
                        if date_match and date_match.group(1).lower() != "null":
                            task_details["due_date"] = date_match.group(1)
                    
                    return task_details
            except Exception as e:
                print(f"Error parsing task details: {e}")
                
            # Fallback
            return {
                "title": task_description[:50],
                "description": task_description,
                "priority": "medium",
                "due_date": None
            }
        except Exception as e:
            print(f"Error extracting task details: {e}")
            return {
                "title": task_description[:50],
                "description": task_description,
                "priority": "medium",
                "due_date": None
            }

    def reflect_on_system(self, days: int = 30) -> dict:
        """Analyze past conversations and system usage to suggest improvements.
        
        This reflection function examines:
        1. Past conversations (chat, coaching sessions)
        2. Tasks, journal entries, and check-ins
        3. User behavior patterns and emotional trends
        
        It provides insights from both productivity methodology (GTD) and 
        cognitive behavioral therapy perspectives.
        
        Args:
            days: Number of days of history to include in the reflection
            
        Returns:
            A dictionary with reflection results
        """
        # Get session history from logger
        from ..logger import SessionLogger
        session_logger = SessionLogger()
        recent_sessions = session_logger.get_recent_sessions(50)  # Get up to 50 recent sessions
        
        # Filter sessions to the specified timeframe
        start_date = datetime.now() - timedelta(days=days)
        recent_sessions = [
            s for s in recent_sessions 
            if datetime.fromisoformat(s["start_time"]) >= start_date
        ]
        
        # Get all recent data from context
        context = self.context_manager.get_recent_context(days=days)
        
        # Extract conversation data from chat sessions
        conversations = []
        for session in recent_sessions:
            if session["type"] == "interactive_chat":
                chat_content = []
                for interaction in session["interactions"]:
                    if interaction.get("type") == "chat":
                        chat_content.append({
                            "user_input": interaction.get("user_input", ""),
                            "response": interaction.get("response", ""),
                            "timestamp": interaction.get("timestamp", "")
                        })
                if chat_content:
                    conversations.append({
                        "session_id": session.get("id", ""),
                        "date": session.get("start_time", ""),
                        "content": chat_content
                    })
        
        # Extract coaching sessions
        coaching_sessions = []
        for session in recent_sessions:
            if session["type"] in ["morning_check_in", "evening_check_in"]:
                for interaction in session["interactions"]:
                    if interaction.get("type") == "coaching":
                        coaching_sessions.append({
                            "session_type": session["type"],
                            "date": session.get("start_time", ""),
                            "response": interaction.get("response", "")
                        })
        
        # Create a comprehensive prompt for the reflection
        prompt = f"""You are an expert system evaluator with deep knowledge of both productivity methodologies (especially GTD - Getting Things Done) and cognitive behavioral therapy (CBT).

Review the following data about a productivity assistant system and its interactions with a user over the past {days} days:

1. CONVERSATION HISTORY:
{json.dumps(conversations[:10], indent=2)}  # Limit to 10 conversations to avoid token limits

2. COACHING SESSIONS:
{json.dumps(coaching_sessions[:5], indent=2)}  # Limit to 5 coaching sessions

3. USER DATA:
- Tasks: {len(context.get('tasks', []))} tasks, {sum(1 for t in context.get('tasks', []) if t.get('status') == 'done')} completed
- Journal Entries: {len(context.get('journal_entries', []))} entries
- Check-ins: {len(context.get('check_ins', []))} check-ins
- User Goals: {json.dumps(context.get('user_goals', []))}
- Emotional States: {len(context.get('emotional_states', []))} recorded states
- Conversation Topics: {json.dumps(list(context.get('conversation_topics', {}).keys()))}

4. SYSTEM CONTEXT:
- Current System Prompt: {self.system_prompt}

Based on this data, provide a comprehensive reflection on:

1. MISSING INFORMATION: What key data or context is missing that would help the system better serve the user?

2. GTD METHODOLOGY ALIGNMENT: How well does the system align with GTD principles? What specific GTD aspects should be enhanced?

3. CBT EFFECTIVENESS: How effectively is the system applying CBT principles to help the user overcome productivity challenges?

4. PROMPT IMPROVEMENTS: Suggest specific improvements to the system prompts to make coaching more effective.

5. FEATURE RECOMMENDATIONS: What new features would significantly enhance the system's value?

6. USER ENGAGEMENT PATTERNS: What patterns emerge in how the user engages with the system? How can these be leveraged?

7. EMOTIONAL SUPPORT: How effectively is the system providing emotional support? How can this be improved?

Structure your response as a JSON object with these sections as keys.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",  # Use GPT-4 for this complex analysis
                messages=[
                    {"role": "system", "content": "You are an expert system evaluator analyzing a productivity assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content
            
            # Extract JSON from response
            try:
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw text
                return {
                    "raw_reflection": response_text,
                    "error": "Failed to parse JSON response"
                }
                
        except Exception as e:
            print(f"Error in system reflection: {e}")
            return {
                "error": str(e),
                "message": "Failed to generate system reflection"
            } 