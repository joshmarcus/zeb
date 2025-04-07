import os
import subprocess
from datetime import datetime, timedelta
import json

def run_command(cmd):
    """Run a command and return its output."""
    print(f"Running command: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")
    if result.stdout:
        print("Output:")
        print(result.stdout)
    if result.returncode != 0 and result.stderr:
        print("Error:")
        print(result.stderr)
    return result.returncode, result.stdout

def setup_environment():
    """Set up the test environment."""
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/logs", exist_ok=True)
    os.makedirs("data/prompts", exist_ok=True)
    os.makedirs("data/context", exist_ok=True)

    # Set up a dummy OpenAI API key for testing
    os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"
    os.environ["OPENAI_API_MOCK"] = "true"  # Enable mock mode for testing

    # Initialize data store files if they don't exist
    data_files = {
        "tasks.json": [],
        "projects.json": [],
        "journal.json": [],
        "checkins.json": [],
        "features.json": [],
        "data_store.json": {}
    }

    for filename, default_content in data_files.items():
        filepath = os.path.join("data", filename)
        if not os.path.exists(filepath):
            with open(filepath, "w") as f:
                json.dump(default_content, f)

    # Initialize session logger file
    sessions_file = os.path.join("data", "sessions.json")
    if not os.path.exists(sessions_file):
        with open(sessions_file, "w") as f:
            json.dump({"sessions": []}, f)

    # Initialize context manager file
    context_file = os.path.join("data/context", "context.json")
    if not os.path.exists(context_file):
        with open(context_file, "w") as f:
            json.dump({
                "current_task": None,
                "current_project": None,
                "current_feature": None,
                "current_session": None
            }, f)

    # Initialize prompt builder file
    versions_file = os.path.join("data/prompts", "versions.json")
    if not os.path.exists(versions_file):
        with open(versions_file, "w") as f:
            json.dump({
                "prompts": [
                    {
                        "prompt": "Default prompt",
                        "timestamp": "2024-01-01T00:00:00Z"
                    }
                ]
            }, f)

def test_task_commands():
    print("\n=== Testing Task Commands ===\n")

    # Test task add
    print("Testing task add...")
    cmd = "py -m src.main task --action add --title \"Test Task\" --description \"A test task\" --priority high --due-date \"2024-12-31\""
    exit_code, output = run_command(cmd)
    assert exit_code == 0, "Task add failed"

    # Test task list
    print("\nTesting task list...")
    cmd = "py -m src.main task --action list"
    exit_code, output = run_command(cmd)
    assert exit_code == 0, "Task list failed"

    # Extract task ID from the list output
    task_id = None
    for line in output.split('\n'):
        if 'Test Task' in line:
            task_id = line.split()[0]
            break
    
    assert task_id is not None, "Could not find task ID"

    # Test task update
    print("\nTesting task update...")
    cmd = f"py -m src.main task --action update --task-id \"{task_id}\" --status \"in_progress\" --priority \"urgent\""
    exit_code, output = run_command(cmd)
    assert exit_code == 0, "Task update failed"

    # Test task delete
    print("\nTesting task delete...")
    cmd = f"py -m src.main task --action delete --task-id \"{task_id}\""
    exit_code, output = run_command(cmd)
    assert exit_code == 0, "Task delete failed"

def test_journal_commands():
    print("\n=== Testing Journal Commands ===\n")

    # Test journal add
    print("Testing journal add...")
    cmd = "py -m src.main journal --content \"Test journal entry\" --type reflection --mood happy"
    exit_code, output = run_command(cmd)
    assert exit_code == 0, "Journal add failed"

    # Test journal list
    print("\nTesting journal list...")
    cmd = "py -m src.main journal --list --days 1"
    exit_code, output = run_command(cmd)
    assert exit_code == 0, "Journal list failed"

    # Test procrastination entry
    print("\nTesting procrastination entry...")
    cmd = "py -m src.main journal --content \"Procrastinating on tests\" --type procrastination --mood anxious"
    exit_code, output = run_command(cmd)
    assert exit_code == 0, "Journal procrastination entry failed"

def test_project_commands():
    print("\n=== Testing Project Commands ===\n")

    # Test project add
    print("Testing project add...")
    cmd = "py -m src.main project --action add --name \"Test Project\" --description \"A test project\""
    exit_code, output = run_command(cmd)
    assert exit_code == 0, "Project add failed"

    # Test project list
    print("\nTesting project list...")
    cmd = "py -m src.main project --action list"
    exit_code, output = run_command(cmd)
    assert exit_code == 0, "Project list failed"

    # Extract project ID from the list output
    project_id = None
    for line in output.split('\n'):
        if 'Test Project' in line:
            # Extract the UUID between the first | characters
            parts = line.split('|')
            if len(parts) >= 2:
                project_id = parts[1].strip()
                break
    
    assert project_id is not None, "Could not find project ID"

    # Test project update
    print("\nTesting project update...")
    cmd = f"py -m src.main project --action update --project-id \"{project_id}\" --status \"in_progress\""
    exit_code, output = run_command(cmd)
    assert exit_code == 0, "Project update failed"

    # Test project delete
    print("\nTesting project delete...")
    cmd = f"py -m src.main project --action delete --project-id \"{project_id}\""
    exit_code, output = run_command(cmd)
    assert exit_code == 0, "Project delete failed"

def test_feature_commands():
    print("\n=== Testing Feature Commands ===\n")

    # Test feature add
    print("Testing feature add...")
    cmd = "py -m src.main feature add --title \"Test Feature\" --description \"A test feature\" --priority high --tags \"test\""
    exit_code, output = run_command(cmd)
    assert exit_code == 0, "Feature add failed"

    # Test feature list
    print("\nTesting feature list...")
    cmd = "py -m src.main feature list"
    exit_code, output = run_command(cmd)
    assert exit_code == 0, "Feature list failed"

    # Extract feature ID from the list output
    feature_id = None
    for line in output.split('\n'):
        if 'Test Feature' in line:
            # Look for the ID in the previous line
            lines = output.split('\n')
            for i, current_line in enumerate(lines):
                if 'Test Feature' in current_line and i > 0:
                    id_line = lines[i-1]
                    if 'ID:' in id_line:
                        feature_id = id_line.split('ID:')[1].strip()
                        break
            break
    
    assert feature_id is not None, "Could not find feature ID"

    # Test feature update
    print("\nTesting feature update...")
    cmd = f"py -m src.main feature update --feature-id \"{feature_id}\" --title \"Updated Test Feature\" --description \"Updated test feature\" --priority high --status \"in_progress\" --notes \"Implementation in progress\""
    exit_code, output = run_command(cmd)
    assert exit_code == 0, "Feature update failed"

    # Test feature delete
    print("\nTesting feature delete...")
    cmd = f"py -m src.main feature delete --feature-id \"{feature_id}\""
    exit_code, output = run_command(cmd)
    assert exit_code == 0, "Feature delete failed"

if __name__ == "__main__":
    print("Starting CLI tests...")
    try:
        setup_environment()
        test_task_commands()
        test_journal_commands()
        test_project_commands()
        test_feature_commands()
        print("\nAll tests completed successfully!")
    except AssertionError as e:
        print(f"\nTest failed: {str(e)}")
        exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        exit(1) 