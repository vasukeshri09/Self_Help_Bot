# 🤖 Self Help Bot — Telegram Task Manager & Reminder Assistant

A lightweight Telegram bot that helps you organize tasks, manage deadlines, and stay on top of your daily responsibilities. Built with Python, SQLite, and the Telegram Bot API, the **Self Help Bot** provides task management, scheduled reminders, persistent storage, and automated cleanup in a Docker-ready application.

> **Stay organized. Track your tasks. Never miss an important deadline.**

## ✨ Features

### 📋 Task Management
- **Create tasks:** Add tasks directly through Telegram.
- **View tasks:** See your tasks, completion status, and deadlines.
- **Complete tasks:** Mark tasks as finished using their IDs.
- **Delete tasks:** Remove tasks manually when they are no longer needed.
- **Deadline support:** Set due dates and times for tasks.
- **Persistent storage:** Tasks are stored in SQLite and remain available after bot restarts.

### ⏰ Smart Reminders
- **Interactive reminder creation:** Create reminders step by step without memorizing a complicated command format.
- **Scheduled notifications:** Receive reminders at the requested date and time.
- **Pending reminder management:** View and cancel standalone reminders.
- **Task-linked reminders:** Automatically associate reminders with tasks that have deadlines.
- **Restart recovery:** Restore pending scheduled reminders when the bot starts again.
- **Automatic cancellation:** Completing or deleting a task removes its associated reminder.

### 🧹 Automatic Task Cleanup
- Automatically remove tasks older than **90 days** when they are eligible for cleanup.
- Clean up both completed tasks and incomplete tasks without future deadlines.
- Preserve tasks that have future deadlines, even when they are older than 90 days.
- Remove task-associated reminders when their tasks are deleted.
- Keep standalone reminders independent of task cleanup.
- Run cleanup on startup and schedule it to run daily.

**Important:** Cleanup permanently deletes eligible task records. Back up or copy important tasks before they reach the retention limit.

### 🐳 Docker Deployment
- Containerized application using Docker.
- Automatic container restart with Docker's `unless-stopped` policy.
- Persistent Docker volume for database storage.
- Environment-variable configuration for sensitive credentials.
- Scheduled jobs powered by the Telegram bot's JobQueue.

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.12 | Application logic |
| `python-telegram-bot` 22.8 | Telegram bot commands and messaging |
| JobQueue / APScheduler | Scheduled reminders and cleanup |
| SQLite | Persistent task and reminder storage |
| `python-dotenv` | Environment variable configuration |
| Docker | Containerization and deployment |
| Git & GitHub | Version control and source code hosting |

---

## 📱 Bot Commands

### Task Management

| Command | Description |
|---|---|
| `/start` | Start the bot and view the welcome message |
| `/help` | Display available commands and usage instructions |
| `/addtask <task>` | Create a task without a deadline |
| `/tasks` | View your tasks and deadlines |
| `/done <id>` | Mark a task as completed |
| `/delete <id>` | Delete a task permanently |

### Creating Tasks with Deadlines

Use a vertical bar (`|`) to separate the task description from its deadline.

**Format:**

```text
/addtask <task description> | DD/MM/YY HH:MM
```

**Example:**

```text
/addtask Submit assignment | 20/10/26 18:30
```

For a task due today, you can provide only the time:

```text
/addtask Study DSA | 18:30
```

All scheduled times use **India Standard Time (IST — Asia/Kolkata)**.

### Reminder Management

| Command | Description |
|---|---|
| `/remind` | Start the interactive reminder creation process |
| `/reminders` | View pending standalone reminders |
| `/cancelreminder <id>` | Cancel a standalone reminder |
| `/cancel` | Cancel an ongoing reminder setup |

When using `/remind`, follow the prompts to provide:

1. A reminder message.
2. A date in `DD/MM/YY` format, or `today`.
3. A time in 24-hour `HH:MM` format.

**Example date and time:**

```text
Date: 20/10/26
Time: 18:30
```

---

## 🚀 Getting Started

You can run the bot locally with Python or deploy it using Docker.

### Prerequisites

- Python 3.12 or compatible Python version.
- A Telegram account.
- A Telegram bot token created using [@BotFather](https://t.me/BotFather).
- Git, if you want to clone the repository.
- Docker Desktop, if you prefer containerized deployment.

### 1. Clone the repository

```bash
git clone https://github.com/vasukeshri09/Self_Help_Bot.git
cd Self_Help_Bot
```

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks environment activation, you can invoke Python directly through the virtual environment instead.

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

The requirements should include the JobQueue extra:

```text
python-telegram-bot[job-queue]==22.8
python-dotenv
```

If your existing `requirements.txt` contains other required packages, retain them as well.

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

Replace the placeholder with the token provided by BotFather.

**Security note:** Never publish your real token, commit `.env` to Git, or share it in screenshots. If a token is exposed, revoke it through BotFather and generate a replacement.

### 5. Start the bot

```bash
python main.py
```

Open your bot in Telegram and send:

```text
/start
```

Use `/help` to explore its commands.

---

## 🐳 Running with Docker

Docker provides an isolated environment for running the bot and makes it easier to restart the application consistently.

### Prerequisites

Install and start [Docker Desktop](https://www.docker.com/products/docker-desktop/), or use a compatible Docker Engine installation.

Ensure that your `.env` file exists in the project root before starting the container.

### 1. Build the Docker image

Run this from the repository directory:

```bash
docker build -t self-help-bot:latest .
```

### 2. Create a persistent database volume

```bash
docker volume create self-help-bot-data
```

### 3. Start the container

```bash
docker run -d \
  --name self-help-bot \
  -v self-help-bot-data:/app/data \
  --env-file .env \
  --restart unless-stopped \
  self-help-bot:latest
```

**Windows PowerShell alternative:**

```powershell
docker run -d --name self-help-bot -v self-help-bot-data:/app/data --env-file .env --restart unless-stopped self-help-bot:latest
```

The named Docker volume stores the SQLite database outside the container's writable filesystem. Recreating the container therefore does not automatically delete the database.

### 4. Verify the container

Check whether the bot is running:

```bash
docker ps
```

Inspect startup logs:

```bash
docker logs --tail 100 self-help-bot
```

Follow logs in real time:

```bash
docker logs -f self-help-bot
```

### 5. Stop, restart, or rebuild

Stop the bot:

```bash
docker stop self-help-bot
```

Restart it:

```bash
docker start self-help-bot
```

Rebuild and recreate the container after changing source code:

```bash
docker stop self-help-bot
docker build --no-cache -t self-help-bot:latest .
docker rm self-help-bot
```

Then run the Docker start command from Step 3 again.

**Database warning:** Do not remove the `self-help-bot-data` volume unless you intentionally want to delete its stored database. Removing the container and removing the volume are different operations.

---

## 🗄️ Database and Data Persistence

The bot uses SQLite to store task and reminder information.

### Tasks

The task records include:

- Task ID
- Telegram user ID
- Task description
- Completion status
- Optional deadline
- Creation timestamp

### Reminders

The reminder records include:

- Reminder ID
- Telegram user ID
- Telegram chat ID
- Reminder message
- Scheduled date and time
- Optional associated task ID

The database is initialized by the application. Existing databases can be upgraded with the schema additions implemented in the database initialization functions.

### Cleanup policy

The automatic cleanup process uses the task creation timestamp to identify records older than 90 days. A task is eligible for deletion when it is older than the retention period and does not have a future deadline.

For existing tasks that predate the creation-timestamp field, the database migration initializes missing timestamps when the migration runs. Consequently, those records may receive a new 90-day retention period starting from migration rather than their original creation date.

---

## 🏗️ Project Structure

The repository is organized around the bot's entry point, command handlers, database operations, and scheduled cleanup.

```text
Self_Help_Bot/
│
├── main.py                  # Bot entry point and handler registration
├── requirements.txt         # Python dependencies
├── Dockerfile               # Docker image configuration
├── .dockerignore            # Excludes unnecessary build files
├── .gitignore               # Excludes local and sensitive files
├── .env                     # Local secrets; not committed
│
├── bot/
│   ├── __init__.py
│   ├── database.py          # SQLite operations and schema migrations
│   ├── todo.py              # Task management commands
│   ├── reminders.py         # Reminder creation and management
│   └── cleaner.py           # Automatic task cleanup
│
└── data/
    └── self_help_bot.db     # Local SQLite database
```

*This is the intended logical structure; filenames should match the actual repository if your local layout differs.*

---

## ⚙️ How It Works

1. A user interacts with the bot through Telegram.
2. The application receives commands and routes them to the relevant handlers.
3. Task and reminder information is saved in SQLite.
4. The JobQueue schedules reminder notifications and daily cleanup.
5. Pending reminders are restored when the application starts.
6. Eligible old tasks and their associated reminders are removed according to the cleanup policy.

---

## 🔒 Security and Reliability

- **Environment variables:** Keep bot credentials outside the source code.
- **Git exclusions:** Do not commit `.env`, virtual environments, Python caches, or local database files.
- **Persistent storage:** Use the named Docker volume for database persistence.
- **User isolation:** Task operations should verify ownership using the Telegram user ID.
- **Reminder recovery:** Pending reminder records are restored during startup.
- **Permanent deletion:** Understand the 90-day retention policy and back up important data when necessary.

A persistent Docker volume is not a substitute for a backup. Periodically back up the SQLite database, especially before major code or schema changes.

---

## 🧪 Testing and Troubleshooting

### Check Python syntax

```bash
python -m compileall -q .
```

### Check container status

```bash
docker ps -a
```

### Inspect application logs

```bash
docker logs --tail 100 self-help-bot
```

### Common issues

| Problem | What to check |
|---|---|
| Bot does not respond | Verify the token, internet access, and startup logs |
| Missing dependency errors | Reinstall dependencies from `requirements.txt` |
| Reminders do not run | Confirm JobQueue dependencies are installed and scheduled jobs are registered |
| Reminders disappear after a restart | Check database persistence and reminder restoration logs |
| Tasks disappear unexpectedly | Review the 90-day cleanup policy and task creation timestamps |
| Database appears empty in Docker | Confirm that the correct named volume is mounted at `/app/data` |
| Docker build fails | Check the Dockerfile, dependency versions, and build output |

---

## 🔮 Potential Future Enhancements

Possible directions for future development include:

- Recurring tasks and recurring reminders.
- Task priorities, categories, and search.
- Daily or weekly productivity summaries.
- Exporting tasks to CSV or PDF.
- Configurable cleanup retention periods.
- Time-zone preferences for users in different regions.
- Automated database backups and restore utilities.
- Unit and integration tests for task, reminder, and cleanup behavior.

These are ideas for future versions, not claims about currently implemented features.

---

## 👨‍💻 Author

**Vasu Keshri**

- GitHub: [@vasukeshri09](https://github.com/vasukeshri09)
- LinkedIn: [Vasu Keshri](https://www.linkedin.com/in/vasu-keshri-394755327/)

## 📄 License

No license is specified here. If you intend to make the repository open source, add a `LICENSE` file and update this section with the chosen license.

---

*Built to make everyday task management simpler, more reliable, and easier to maintain.*
