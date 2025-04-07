# Roy - Your Terminal-Based Productivity Assistant

Roy is a powerful terminal-based productivity assistant that helps you manage your daily tasks, projects, and reflections using a GTD-style workflow. It features AI-powered coaching to help you stay focused and productive.

## Features

- 📅 Daily check-ins (morning and evening)
- ✅ Task management with GTD workflow
- 📝 Journaling with mood tracking
- 📊 Project organization
- 🤖 AI-powered coaching and insights
- 💾 JSON-based data persistence
- 🎨 Beautiful terminal UI with Rich

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/productivity-assistant.git
cd productivity-assistant
```

2. Create and activate a virtual environment:
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. Install the package in development mode:
```bash
pip install -e ".[dev]"
```

## Configuration

### OpenAI API Key

Roy uses OpenAI's GPT-4 for coaching and insights. You'll need to set up your API key:

1. Get your API key from [OpenAI's platform](https://platform.openai.com/api-keys)

2. Create a `.env` file in the project root:
```bash
touch .env
```

3. Add your API key to the `.env` file:
```
OPENAI_API_KEY=your-api-key-here
```

## Usage

Once installed, you can use Roy from anywhere in your terminal by typing `roy` followed by the command:

### Daily Check-ins

```bash
# Morning check-in
roy check-in --time morning

# Evening check-in
roy check-in --time evening
```

### Task Management

```bash
# Add a new task
roy task --action add

# List all tasks
roy task --action list

# Complete a task
roy task --action complete --task-id <task-id>
```

### Journaling

```bash
# Add a journal entry
roy journal --content "Today I..." --reflection-type reflection --mood happy

# Add a procrastination reflection
roy journal --content "I'm procrastinating on..." --reflection-type procrastination --mood anxious
```

### Project Management

```bash
# Add a new project
roy project --action add

# List all projects
roy project --action list

# Add a task to a project
roy task --action add --project-id <project-id>
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=term-missing
```

### Code Style

The project uses:
- Black for code formatting
- isort for import sorting
- mypy for type checking

```bash
# Format code
black .

# Sort imports
isort .

# Type check
mypy src
```

## Project Structure

```
productivity_assistant/
├── src/
│   ├── llm/
│   │   └── coach.py
│   ├── models/
│   │   └── base.py
│   ├── storage/
│   │   └── data_store.py
│   └── main.py
├── tests/
│   ├── test_coach.py
│   ├── test_data_store.py
│   └── test_main.py
├── data/
│   ├── tasks.json
│   ├── projects.json
│   ├── journal.json
│   └── checkins.json
├── .env
├── .gitignore
├── pyproject.toml
├── setup.py
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 