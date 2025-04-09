import os
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
from pathlib import Path
import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
import click

from .models.base import (
    CheckIn, JournalEntry, Priority, Project, Task, TaskStatus,
    FeatureRequest, FeatureStatus
)
from .storage.data_store import DataStore
from .llm.coach import ProductivityCoach
from .llm.prompt_builder import PromptBuilder
from .context import ContextManager
from .logger import SessionLogger

app = typer.Typer(help="Productivity Assistant - Your daily productivity coach")
console = Console()

# Initialize singletons
_data_store = None
_coach = None

def get_data_store() -> DataStore:
    """Get the singleton data store instance."""
    global _data_store
    if _data_store is None:
        _data_store = DataStore()
    return _data_store

def get_coach() -> ProductivityCoach:
    """Get the singleton coach instance."""
    global _coach
    if _coach is None:
        _coach = ProductivityCoach(get_data_store())
    return _coach

data_store = get_data_store()
coach = get_coach()
prompt_builder = PromptBuilder(data_store)
context_manager = ContextManager(data_store)
session_logger = SessionLogger()

# Set the context manager on the coach
coach.context_manager = context_manager

@app.command()
def check_in_morning():
    """Start a morning check-in session."""
    session_id = session_logger.start_session("morning_check_in")
    try:
        # Get recent context first
        context = context_manager.get_recent_context()
        
        # Build the morning prompt
        prompt = prompt_builder.build_morning_prompt(context)
        
        # Get coaching insights
        response = coach.get_morning_coaching(prompt)
        
        session_logger.log_interaction(session_id, {
            "type": "coaching",
            "response": response,
            "context": context
        })
        
        console.print(Panel(response, title="Morning Check-in Insights"))
    finally:
        session_logger.end_session(session_id)


@app.command()
def check_in_evening():
    """Start an evening check-in session."""
    session_id = session_logger.start_session("evening_check_in")
    try:
        # Get recent context first
        context = context_manager.get_recent_context()
        
        # Build the evening prompt
        prompt = prompt_builder.build_evening_prompt(context)
        
        # Get coaching insights
        response = coach.get_evening_coaching(prompt)
        
        session_logger.log_interaction(session_id, {
            "type": "coaching",
            "response": response,
            "context": context
        })
        
        console.print(Panel(response, title="Evening Check-in Insights"))
    finally:
        session_logger.end_session(session_id)


@app.command()
def task(
    action: str = typer.Option(..., help="Action to perform (add/list/update/delete)"),
    task_id: Optional[str] = typer.Option(None, "--task-id", "-t", help="Task ID for update/delete operations"),
    title: Optional[str] = typer.Option(None, "--title", help="Task title"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Task description"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="Task priority (low/medium/high/urgent)"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Task status (todo/in_progress/blocked/done)"),
    due_date: Optional[str] = typer.Option(None, "--due-date", help="Due date in YYYY-MM-DD format"),
    suggest_subtasks: bool = typer.Option(False, "--suggest-subtasks", help="Use AI to suggest subtasks")
):
    """Manage tasks."""
    if action == "add":
        session_id = session_logger.start_session("task_add")
        try:
            # For add action, require title and skip prompts if all required fields are provided
            if not title:
                final_title = Prompt.ask("Task title")
            else:
                final_title = title

            if not description:
                final_description = Prompt.ask("Task description", default="")
            else:
                final_description = description

            if not priority:
                priority_str = Prompt.ask(
                    "Priority",
                    choices=["low", "medium", "high", "urgent"],
                    default="medium",
                )
            else:
                priority_str = priority

            if not due_date:
                final_due_date_str = Prompt.ask("Due date (YYYY-MM-DD)", default="")
            else:
                final_due_date_str = due_date
            
            task = Task(
                title=final_title,
                description=final_description,
                priority=Priority(priority_str),
                due_date=datetime.strptime(final_due_date_str, "%Y-%m-%d") if final_due_date_str else None,
            )
            
            # Prompt for subtasks if suggest_subtasks is not explicitly provided
            should_suggest = suggest_subtasks
            if not suggest_subtasks:
                should_suggest = Prompt.ask("Would you like AI to suggest subtasks?", choices=["y", "n"], default="n") == "y"
            
            if should_suggest:
                subtasks = coach.suggest_task_breakdown(task)
                for subtask in subtasks:
                    task.subtasks.append(Task(title=subtask))
            
            session_logger.log_interaction(session_id, {
                "type": "task_creation",
                "task": task.model_dump()
            })
            
            data_store.save(task)
            console.print("[green]Task added successfully![/green]")
        finally:
            session_logger.end_session(session_id)

    elif action == "list":
        session_id = session_logger.start_session("task_list")
        try:
            tasks = data_store.get_all(Task)
            # Print header
            console.print("\nID                                     Title                Status     Priority   Due Date")
            console.print("-" * 100)
            
            # Print tasks
            for task in tasks:
                console.print(
                    f"{str(task.id):<36} "
                    f"{task.title:<20} "
                    f"{task.status.value:<10} "
                    f"{task.priority.value:<10} "
                    f"{task.due_date.strftime('%Y-%m-%d') if task.due_date else ''}"
                )
            
            session_logger.log_interaction(session_id, {
                "type": "task_list",
                "tasks": [task.model_dump() for task in tasks]
            })
        finally:
            session_logger.end_session(session_id)

    elif action in ["update", "delete"] and not task_id:
        console.print("[red]Error: task_id is required for update/delete operations[/red]")
        raise typer.Exit(1)

    elif action == "update":
        task = data_store.get_by_id(Task, task_id)
        if not task:
            console.print("[red]Error: Task not found[/red]")
            raise typer.Exit(1)

        if title:
            task.title = title
        if description:
            task.description = description
        if status:
            try:
                task.status = TaskStatus(status)
            except ValueError:
                console.print(f"[red]Invalid status: {status}. Using current status.[/red]")
        if priority:
            try:
                task.priority = Priority(priority)
            except ValueError:
                console.print(f"[red]Invalid priority: {priority}. Using current priority.[/red]")
        
        data_store.save(task)
        console.print("[green]Task updated successfully![/green]")

    elif action == "delete":
        if data_store.delete(Task, task_id):
            console.print("[green]Task deleted successfully![/green]")
        else:
            console.print("[red]Error: Task not found[/red]")
            raise typer.Exit(1)


@app.command()
def journal(
    content: Optional[str] = typer.Option(None, "--content", "-c", help="Journal entry content"),
    reflection_type: Optional[str] = typer.Option(
        None,
        "--type", "-t",
        help="Type of reflection (morning_checkin/evening_review/procrastination/anxiety/reflection)",
    ),
    mood: Optional[str] = typer.Option(None, "--mood", "-m", help="Current mood"),
    list_entries: bool = typer.Option(False, "--list", "-l", help="List recent journal entries"),
    days: int = typer.Option(7, "--days", "-d", help="Number of days of entries to show when listing")
):
    """Add or list journal entries."""
    if list_entries:
        entries = data_store.get_journal_entries_by_date(datetime.now() - timedelta(days=days))
        if not entries:
            console.print("No journal entries found for the specified period.")
            return
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date")
        table.add_column("Type")
        table.add_column("Mood")
        table.add_column("Content")
        
        for entry in entries:
            table.add_row(
                entry.timestamp.strftime("%Y-%m-%d %H:%M"),
                entry.reflection_type,
                entry.mood or "",
                entry.content[:100] + "..." if len(entry.content) > 100 else entry.content,
            )
        
        console.print(table)
        return

    session_id = session_logger.start_session("journal_add")
    try:
        # If not listing, we need content and type
        final_content = content
        final_type = reflection_type
        final_mood = mood

        if not final_content:
            final_content = Prompt.ask("Journal entry content")
        
        if not final_type:
            final_type = Prompt.ask(
                "Type of reflection",
                choices=["morning_checkin", "evening_review", "procrastination", "anxiety", "reflection"],
                default="reflection"
            )
        
        if not final_mood:
            final_mood = Prompt.ask("Current mood", default="")

        entry = JournalEntry(
            content=final_content,
            reflection_type=final_type,
            mood=final_mood,
            timestamp=datetime.now()
        )
        
        session_logger.log_interaction(session_id, {
            "type": "journal_entry",
            "entry": entry.model_dump()
        })
        
        data_store.save(entry)
        
        # If it's a procrastination entry, get insights
        if final_type == "procrastination":
            prompt = prompt_builder.build_procrastination_prompt(entry)
            insights = coach.analyze_procrastination(prompt)
            
            session_logger.log_interaction(session_id, {
                "type": "procrastination_analysis",
                "insights": insights
            })
            
            console.print("\nProcrastination Insights:")
            console.print(Panel(insights))
        
        console.print("[green]Journal entry added successfully![/green]")
    finally:
        session_logger.end_session(session_id)


@app.command()
def project(
    action: str = typer.Option(..., help="Action to perform (add/list/update/delete)"),
    project_id: Optional[str] = typer.Option(None, "--project-id", "-p", help="Project ID for update/delete operations"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Project name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Project description"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Project status (todo/in_progress/blocked/done)")
):
    """Manage projects."""
    if action == "add":
        session_id = session_logger.start_session("project_add")
        try:
            # For add action, require name and skip prompts if all required fields are provided
            if not name:
                final_name = Prompt.ask("Project name")
            else:
                final_name = name

            if not description:
                final_description = Prompt.ask("Project description", default="")
            else:
                final_description = description

            project = Project(
                name=final_name,
                description=final_description
            )
            
            session_logger.log_interaction(session_id, {
                "type": "project_creation",
                "project": project.model_dump()
            })
            
            data_store.save(project)
            console.print("[green]Project added successfully![/green]")
        finally:
            session_logger.end_session(session_id)

    elif action == "list":
        session_id = session_logger.start_session("project_list")
        try:
            projects = data_store.get_all(Project)
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID")
            table.add_column("Name")
            table.add_column("Status")
            table.add_column("Tasks")
            
            for project in projects:
                tasks = data_store.get_tasks_by_project(project.id)
                table.add_row(
                    str(project.id),
                    project.name,
                    project.status.value,
                    str(len(tasks))
                )
            
            session_logger.log_interaction(session_id, {
                "type": "project_list",
                "projects": [project.model_dump() for project in projects]
            })
            
            console.print(table)
        finally:
            session_logger.end_session(session_id)

    elif action in ["update", "delete"] and not project_id:
        console.print("[red]Error: project_id is required for update/delete operations[/red]")
        raise typer.Exit(1)

    elif action == "update":
        session_id = session_logger.start_session("project_update")
        try:
            project = data_store.get_by_id(Project, project_id)
            if not project:
                console.print("[red]Error: Project not found[/red]")
                raise typer.Exit(1)

            if name:
                project.name = name
            if description:
                project.description = description
            if status:
                try:
                    project.status = TaskStatus(status)
                except ValueError:
                    console.print(f"[red]Invalid status: {status}. Using current status.[/red]")
            
            session_logger.log_interaction(session_id, {
                "type": "project_update",
                "project": project.model_dump()
            })
            
            data_store.save(project)
            console.print("[green]Project updated successfully![/green]")
        finally:
            session_logger.end_session(session_id)

    elif action == "delete":
        session_id = session_logger.start_session("project_delete")
        try:
            if data_store.delete(Project, project_id):
                session_logger.log_interaction(session_id, {
                    "type": "project_delete",
                    "project_id": project_id
                })
                console.print("[green]Project deleted successfully![/green]")
            else:
                console.print("[red]Error: Project not found[/red]")
                raise typer.Exit(1)
        finally:
            session_logger.end_session(session_id)


@app.command()
def analyze_patterns():
    """Analyze productivity patterns."""
    session_id = session_logger.start_session("pattern_analysis")
    try:
        patterns = context_manager.analyze_productivity_patterns()
        
        console.print("\nProductivity Analysis:")
        console.print(f"Task Completion Rate: {patterns['task_completion_rate']:.1%}")
        
        if patterns['common_procrastination_triggers']:
            console.print("\nCommon Procrastination Triggers:")
            for trigger in patterns['common_procrastination_triggers']:
                console.print(f"- {trigger}")
        
        if patterns['productive_times']['most_productive_hours']:
            console.print("\nMost Productive Hours:")
            for hour, count in patterns['productive_times']['most_productive_hours']:
                console.print(f"- {hour:02d}:00 ({count} sessions)")
        
        if patterns['goal_progress']:
            console.print("\nGoal Progress:")
            for goal, progress in patterns['goal_progress'].items():
                console.print(f"\n{goal}:")
                console.print(f"- Completed Tasks: {progress['completed_tasks']}/{progress['total_tasks']}")
                console.print(f"- Journal Mentions: {progress['journal_mentions']}")
        
        session_logger.log_interaction(session_id, {
            "type": "pattern_analysis",
            "patterns": patterns
        })
    finally:
        session_logger.end_session(session_id)


@app.command()
def feedback(
    content: str = typer.Option(..., prompt=True),
    rating: int = typer.Option(..., prompt=True)
):
    """Provide feedback to improve the assistant."""
    session_id = session_logger.start_session("feedback")
    try:
        # Update system prompt based on feedback
        new_prompt = prompt_builder.update_system_prompt(content)
        
        # Update assistant adaptations
        context_manager.update_assistant_adaptations({
            "feedback": content,
            "rating": rating,
            "timestamp": datetime.now().isoformat()
        })
        
        session_logger.log_interaction(session_id, {
            "type": "feedback",
            "content": content,
            "rating": rating
        })
        
        console.print("Thank you for your feedback! The assistant will adapt based on your input.")
    finally:
        session_logger.end_session(session_id)


@app.command()
def feature(
    action: str = typer.Argument(..., help="Action to perform: add, list, update, delete"),
    feature_id: Optional[str] = typer.Option(None, "--feature-id", "-f", help="Feature ID for update/delete operations"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Natural language description of the feature request"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Title of the feature request"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="Priority of the feature request (low/medium/high)"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Status of the feature request (pending/in_progress/completed/rejected)"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated list of tags"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Implementation notes or rejection reason")
):
    """Manage feature requests."""
    data_store = get_data_store()
    coach = get_coach()
    
    if action == "add":
        # Get natural language description from command line or prompt
        if description is None:
            description = typer.prompt("Describe your feature request in natural language")
        
        # Expand the feature request using the coach
        expanded = coach.expand_feature_request(description)
        
        # Show the expanded feature request to the user
        typer.echo("\nI've analyzed your request and expanded it into the following:")
        typer.echo(f"\nTitle: {expanded['title']}")
        typer.echo(f"Description: {expanded['description']}")
        typer.echo(f"Priority: {expanded['priority']}")
        typer.echo(f"Tags: {', '.join(expanded['tags'])}")
        
        # If all parameters are provided via command line, skip confirmation
        if all([title, priority]):
            create_feature = True
        else:
            create_feature = typer.confirm("\nWould you like to create this feature request?")
        
        if not create_feature:
            typer.echo("Feature request cancelled.")
            return
            
        # Use command line arguments if provided, otherwise prompt
        final_title = title or typer.prompt("Title", default=expanded['title'])
        final_description = description or expanded['description']
        priority_str = priority or typer.prompt(
            "Priority (low/medium/high)",
            default=expanded['priority']
        ).upper()
        
        try:
            final_priority = Priority[priority_str]
        except KeyError:
            typer.echo(f"Invalid priority: {priority_str}. Using MEDIUM as default.")
            final_priority = Priority.MEDIUM
            
        final_tags = []
        if tags:
            final_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        else:
            tags_input = typer.prompt(
                "Tags (comma-separated)",
                default=",".join(expanded['tags'])
            )
            final_tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
            
        feature = FeatureRequest(
            title=final_title,
            description=final_description,
            priority=final_priority,
            tags=final_tags
        )
        
        data_store.save(feature)
        typer.echo("Feature request added successfully!")
        
    elif action == "list":
        features = data_store.get_all(FeatureRequest)
        if not features:
            typer.echo("No feature requests found.")
            return
            
        for feature in features:
            typer.echo(f"\nID: {feature.id}")
            typer.echo(f"Title: {feature.title}")
            typer.echo(f"Description: {feature.description}")
            typer.echo(f"Status: {feature.status.name}")
            typer.echo(f"Priority: {feature.priority.name}")
            typer.echo(f"Tags: {', '.join(feature.tags)}")
            if feature.implementation_notes:
                typer.echo(f"Implementation Notes: {feature.implementation_notes}")
            if feature.rejection_reason:
                typer.echo(f"Rejection Reason: {feature.rejection_reason}")
                
    elif action == "update":
        if not feature_id:
            typer.echo("Feature ID is required for update operation.")
            raise typer.Exit(1)
            
        feature = data_store.get_by_id(FeatureRequest, feature_id)
        if not feature:
            typer.echo(f"Feature with ID {feature_id} not found.")
            raise typer.Exit(1)
            
        # If all parameters are provided via command line, skip prompts
        if all([title, description, priority, status]):
            try:
                priority = Priority[priority.upper()]
            except KeyError:
                typer.echo(f"Invalid priority: {priority}. Keeping current priority.")
                priority = feature.priority
                
            try:
                status = FeatureStatus[status.upper()]
            except KeyError:
                typer.echo(f"Invalid status: {status}. Keeping current status.")
                status = feature.status
                
            feature.title = title
            feature.description = description
            feature.priority = priority
            
            if status == FeatureStatus.IN_PROGRESS and notes:
                feature.update_status(status, notes)
            elif status == FeatureStatus.REJECTED and notes:
                feature.update_status(status, notes)
            else:
                feature.status = status
                
            if tags:
                feature.tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        else:
            # Interactive mode
            title = typer.prompt("Enter new title", default=feature.title)
            description = typer.prompt("Enter new description", default=feature.description)
            priority_str = typer.prompt("Enter new priority (low/medium/high)", default=feature.priority.name).upper()
            status_str = typer.prompt("Enter new status (pending/in_progress/completed/rejected)", default=feature.status.name).upper()
            
            try:
                priority = Priority[priority_str]
            except KeyError:
                typer.echo(f"Invalid priority: {priority_str}. Keeping current priority.")
                priority = feature.priority
                
            try:
                status = FeatureStatus[status_str]
            except KeyError:
                typer.echo(f"Invalid status: {status_str}. Keeping current status.")
                status = feature.status
                
            if status == FeatureStatus.IN_PROGRESS:
                notes = typer.prompt("Enter implementation notes")
                feature.update_status(status, notes)
            elif status == FeatureStatus.REJECTED:
                reason = typer.prompt("Enter rejection reason")
                feature.update_status(status, reason)
            else:
                feature.status = status
                
            feature.title = title
            feature.description = description
            feature.priority = priority
            
            tags = typer.prompt("Enter new tags (comma-separated)", default=",".join(feature.tags)).split(",")
            feature.tags = [tag.strip() for tag in tags if tag.strip()]
        
        data_store.save(feature)
        typer.echo("Feature request updated successfully!")
        
    elif action == "delete":
        if not feature_id:
            typer.echo("Feature ID is required for delete operation.")
            raise typer.Exit(1)
            
        feature = data_store.get_by_id(FeatureRequest, feature_id)
        if not feature:
            typer.echo(f"Feature with ID {feature_id} not found.")
            raise typer.Exit(1)
            
        data_store.delete(FeatureRequest, feature_id)
        typer.echo("Feature request deleted successfully!")
        
    else:
        typer.echo(f"Invalid action: {action}. Valid actions are: add, list, update, delete")
        raise typer.Exit(1)


@app.command()
def chat():
    """Start an interactive coaching session with Zeb."""
    session_id = session_logger.start_session("interactive_chat")
    try:
        console.print(Panel.fit(
            "[bold green]Welcome to your interactive coaching session with Zeb![/bold green]\n"
            "You can chat freely about your tasks, priorities, emotions, or challenges.\n"
            "Type [bold cyan]'exit'[/bold cyan] or [bold cyan]'quit'[/bold cyan] to end the session.\n\n"
            "Special commands:\n"
            "- [bold cyan]create task: [description][/bold cyan] - Add a new task\n"
            "- [bold cyan]help[/bold cyan] - Show available commands",
            title="Interactive Coaching Session"
        ))
        
        # Get initial context and greeting
        context = context_manager.get_recent_context()
        greeting = coach.generate_chat_response("Greet the user and ask about their current priorities and how they're feeling today.", context)
        console.print(f"[bold blue]Zeb:[/bold blue] {greeting}")
        
        chat_history = [{"role": "assistant", "content": greeting}]
        
        while True:
            # Get user input
            user_input = Prompt.ask("[bold green]You[/bold green]")
            
            # Check for exit commands
            if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
                farewell = coach.generate_chat_response("The user is ending the session. Provide a brief, encouraging farewell.", context, chat_history)
                console.print(f"[bold blue]Zeb:[/bold blue] {farewell}")
                break
                
            # Check for help command
            if user_input.lower() == "help":
                console.print(Panel.fit(
                    "Available commands:\n"
                    "- [bold cyan]create task: [description][/bold cyan] - Add a new task\n"
                    "- [bold cyan]list tasks[/bold cyan] - Show your current tasks\n"
                    "- [bold cyan]how am I doing?[/bold cyan] - Get an assessment of your progress\n"
                    "- [bold cyan]help[/bold cyan] - Show this help message\n"
                    "- [bold cyan]exit[/bold cyan] or [bold cyan]quit[/bold cyan] - End the session",
                    title="Help"
                ))
                continue
                
            # Check for list tasks command
            if user_input.lower() == "list tasks":
                tasks = data_store.get_all(Task)
                if not tasks:
                    console.print("You don't have any tasks yet.")
                else:
                    console.print("\nYour current tasks:")
                    for task in tasks:
                        status_color = {
                            "pending": "yellow",
                            "in_progress": "blue",
                            "done": "green",
                            "blocked": "red"
                        }.get(task.status.value, "white")
                        
                        console.print(f"[{status_color}]• {task.title} ({task.priority.value})[/{status_color}]")
                continue
                
            # Process task creation command
            if user_input.lower().startswith("create task:") or user_input.lower().startswith("add task:"):
                task_description = user_input.split(":", 1)[1].strip()
                
                # Extract task details using the coach
                task_details = coach.extract_task_details(task_description, context)
                
                # Create task with extracted details
                task = Task(
                    title=task_details.get("title", task_description[:50]),
                    description=task_details.get("description", task_description),
                    priority=Priority(task_details.get("priority", "medium")),
                    due_date=datetime.strptime(task_details.get("due_date"), "%Y-%m-%d") if task_details.get("due_date") else None,
                )
                
                data_store.save(task)
                console.print("[green]Task added successfully![/green]")
                
                # Get confirmation and next steps from coach
                response = coach.generate_chat_response(
                    f"The user has created a task: {task_description}. Confirm the task was created and ask if they want to break it down or add more details.",
                    context,
                    chat_history
                )
                console.print(f"[bold blue]Zeb:[/bold blue] {response}")
                chat_history.append({"role": "user", "content": user_input})
                chat_history.append({"role": "assistant", "content": response})
                
                # Track task creation as a topic
                context_manager.track_conversation_topic("task_management", 3)
                continue
            
            # Add user input to chat history
            chat_history.append({"role": "user", "content": user_input})
            
            # Look for emotional cues and track them
            emotion_keywords = {
                "anxious": ("anxiety", 7),
                "anxiety": ("anxiety", 7),
                "worried": ("anxiety", 5),
                "stressed": ("stress", 6),
                "overwhelmed": ("overwhelm", 8),
                "procrastinating": ("procrastination", 6),
                "unmotivated": ("lack_of_motivation", 6),
                "stuck": ("stuck", 5),
                "tired": ("fatigue", 4),
                "exhausted": ("fatigue", 7),
                "frustrated": ("frustration", 6),
                "happy": ("happiness", 6),
                "excited": ("excitement", 7),
                "motivated": ("motivation", 8),
                "productive": ("productivity", 7),
                "focused": ("focus", 7)
            }
            
            for keyword, (emotion, intensity) in emotion_keywords.items():
                if keyword in user_input.lower():
                    # Store the emotional state
                    context_manager.store_emotional_state(emotion, intensity, user_input)
                    # Track it as a conversation topic
                    context_manager.track_conversation_topic(emotion, intensity // 2)
            
            # Track conversation topics
            topic_keywords = {
                "prioritize": "prioritization",
                "priorities": "prioritization",
                "important": "prioritization",
                "urgent": "prioritization",
                "focus": "focus",
                "plan": "planning",
                "schedule": "planning",
                "goals": "goal_setting",
                "goal": "goal_setting",
                "productivity": "productivity",
                "habit": "habit_formation",
                "routine": "routines",
                "distract": "distractions",
                "procrastinate": "procrastination",
                "time management": "time_management",
                "balance": "work_life_balance",
                "health": "health",
                "sleep": "sleep",
                "exercise": "exercise",
                "work": "work",
                "study": "study",
                "project": "projects"
            }
            
            for keyword, topic in topic_keywords.items():
                if keyword in user_input.lower():
                    context_manager.track_conversation_topic(topic, 2)
            
            # Generate response based on identified topics
            if any(kw in user_input.lower() for kw in ["anxious", "anxiety", "worried", "stress", "overwhelm", "procrastinate", "procrastinating"]):
                # Focus on emotional support in response
                response = coach.generate_chat_response(
                    f"The user is expressing emotional concerns: {user_input}. Provide empathetic support and practical advice for managing these feelings.",
                    context,
                    chat_history
                )
            elif any(kw in user_input.lower() for kw in ["prioritize", "priorities", "important", "urgent", "focus", "plan"]):
                # Focus on prioritization in response
                response = coach.generate_chat_response(
                    f"The user is asking about priorities or planning: {user_input}. Help them clarify priorities and create a plan.",
                    context,
                    chat_history
                )
            elif "how am I doing" in user_input.lower():
                # Analyze patterns and provide an assessment
                patterns = context_manager.analyze_productivity_patterns()
                # Add this to the context
                context["productivity_patterns"] = patterns
                response = coach.generate_chat_response(
                    f"The user wants to know how they're doing. Use the productivity patterns to provide an encouraging assessment of their progress.",
                    context,
                    chat_history
                )
            else:
                # General response
                response = coach.generate_chat_response(user_input, context, chat_history)
                
            # Add assistant response to chat history
            chat_history.append({"role": "assistant", "content": response})
            
            # Display the response
            console.print(f"[bold blue]Zeb:[/bold blue] {response}")
            
            # Log interaction
            session_logger.log_interaction(session_id, {
                "type": "chat",
                "user_input": user_input,
                "response": response
            })
            
            # Update context after several exchanges
            if len(chat_history) % 6 == 0:
                context = context_manager.get_recent_context()
            
    finally:
        # End session and add memory item about topics discussed
        if len(chat_history) > 2:
            topics_discussed = []
            if "conversation_topics" in context:
                topics_discussed = list(context["conversation_topics"].keys())[:3]
            
            context_manager.add_to_assistant_memory({
                "type": "chat_session",
                "topics": topics_discussed,
                "messages_count": len(chat_history) // 2,
                "session_id": session_id
            })
            
        session_logger.end_session(session_id)


@app.command()
def reflect(
    days: int = typer.Option(30, "--days", "-d", help="Number of days of history to include in reflection"),
    save_to_file: bool = typer.Option(False, "--save", "-s", help="Save reflection results to file"),
    format_json: bool = typer.Option(False, "--json", "-j", help="Output raw JSON")
):
    """Reflect on system performance and suggest improvements based on GTD and CBT principles."""
    console.print(Panel.fit(
        "[bold blue]Starting system reflection...[/bold blue]\n"
        "Analyzing past conversations, user data, and system performance.\n"
        "This may take a minute as it processes your usage patterns.",
        title="System Reflection"
    ))
    
    session_id = session_logger.start_session("system_reflection")
    try:
        # Initialize the coach with the context manager
        if not coach.context_manager:
            coach.context_manager = context_manager
            
        # Get the reflection
        reflection = coach.reflect_on_system(days=days)
        
        if "error" in reflection:
            console.print(f"[red]Error during reflection: {reflection['error']}[/red]")
            if "raw_reflection" in reflection:
                console.print(Panel(reflection["raw_reflection"], title="Raw Reflection Output"))
            return
            
        # Save to file if requested
        if save_to_file:
            reflection_dir = Path("data/reflections")
            reflection_dir.mkdir(parents=True, exist_ok=True)
            reflection_file = reflection_dir / f"reflection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            reflection_file.write_text(json.dumps(reflection, indent=2))
            console.print(f"[green]Reflection saved to {reflection_file}[/green]")
            
        # Return raw JSON if requested
        if format_json:
            console.print(json.dumps(reflection, indent=2))
            return
            
        # Display formatted reflection
        console.print("\n[bold blue]== System Reflection Results ==[/bold blue]\n")
        
        # Missing Information
        console.print(Panel(
            reflection.get("MISSING_INFORMATION", "No data available"),
            title="[bold]Missing Information[/bold]",
            border_style="blue"
        ))
        
        # GTD Methodology Alignment
        console.print(Panel(
            reflection.get("GTD_METHODOLOGY_ALIGNMENT", "No data available"),
            title="[bold]GTD Methodology Alignment[/bold]",
            border_style="green"
        ))
        
        # CBT Effectiveness
        console.print(Panel(
            reflection.get("CBT_EFFECTIVENESS", "No data available"),
            title="[bold]CBT Effectiveness[/bold]",
            border_style="magenta"
        ))
        
        # Prompt Improvements
        console.print(Panel(
            reflection.get("PROMPT_IMPROVEMENTS", "No data available"),
            title="[bold]Prompt Improvements[/bold]",
            border_style="yellow"
        ))
        
        # Feature Recommendations
        console.print(Panel(
            reflection.get("FEATURE_RECOMMENDATIONS", "No data available"),
            title="[bold]Feature Recommendations[/bold]",
            border_style="cyan"
        ))
        
        # User Engagement Patterns
        console.print(Panel(
            reflection.get("USER_ENGAGEMENT_PATTERNS", "No data available"),
            title="[bold]User Engagement Patterns[/bold]",
            border_style="red"
        ))
        
        # Emotional Support
        console.print(Panel(
            reflection.get("EMOTIONAL_SUPPORT", "No data available"),
            title="[bold]Emotional Support[/bold]",
            border_style="purple"
        ))
        
        # Log the reflection
        session_logger.log_interaction(session_id, {
            "type": "system_reflection",
            "reflection": reflection
        })
        
        console.print("\n[green]Reflection complete![/green] Use these insights to guide system improvements.")
        
    finally:
        session_logger.end_session(session_id)


def main():
    """Run the application."""
    app()


if __name__ == "__main__":
    main() 