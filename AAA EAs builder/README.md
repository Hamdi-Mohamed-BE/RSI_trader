# AAA EAs Builder

An early production-shaped Django foundation for an AI-assisted MT5 EA and Pine strategy builder with an evidence-first marketplace.

## What is implemented

- Django 5.2 LTS project with a custom email-based user model.
- Class-based customer views for authentication, dashboard, projects, and marketplace pages.
- Tailwind cyberpunk trading interface based on the approved mockups.
- Unfold-powered staff admin.
- Encrypted, write-only AI gateway credentials and versioned model/agent/workflow records.
- Environment-seeded Gemini gateway and model configuration, managed through Unfold admin.
- Admin-managed, versioned architect/generator/reviewer/repairer workflow.
- Working MQL5 and Pine generation with bounded repair loops and token accounting.
- Versioned source storage, deterministic validation, progress pages, revisions, and protected downloads.
- Project-aware generation chat with live progress/code/diagnostic context and reviewable fixes.
- Optional allowlisted MetaEditor compilation with separate compiler evidence.
- Project, generation, code-version, product, and test-evidence models.
- Celery/Redis integration and worker health task.
- Safe fictional marketplace seed data.
- SQLite development database with a PostgreSQL-ready ORM design.
- Normal Windows and Docker workflows.

Checkout, entitlements, and protected marketplace product downloads are intentionally deferred to their own milestones. MQL5 compilation is available only when an isolated Windows MetaEditor installation is explicitly configured; the application never treats AI review or static checks as proof of compilation.

## Normal Windows setup

```bat
dev.bat setup
dev.bat superuser
dev.bat all
```

Open `http://127.0.0.1:8000`. The staff admin is at `http://127.0.0.1:8000/admin/`.

`dev.bat all` opens the Tailwind watcher and Celery worker in separate windows, then runs the Django website in the current window. Redis must be reachable for background jobs; the core website works without executing a Celery task.

`dev.bat setup` and `dev.bat web` synchronize `GEMINI_API_KEY` and `GEMINI_MODEL` from the ignored `.env` file into the database. The API key is encrypted before storage and is never displayed again in admin. Use `dev.bat sync-ai` after changing either value without restarting the website.

In normal development, generation runs inline so the builder works without a local Redis service. Docker uses Celery and Redis for background execution with progress polling. Create a project, open its workspace, and choose **Generate code** to start the pinned multi-agent workflow.

Every generation page also includes a project-aware copilot. Its context is rebuilt for each answer from the current project specification, run progress, pinned workflow snapshot, latest complete source, version metadata, validation diagnostics, compiler output, and the latest 20 chat messages. A requested code fix is stored as a complete proposal tied to its base version. It changes nothing until the project owner chooses **Apply as new version**, which preserves the original, reruns deterministic validation, and invokes the optional compiler when configured. Project source and conversation content are sent to the configured AI gateway when the copilot is used.

## Optional MQL5 compiler

Generated MQL5 is never executed by the website. To enable compile-only MetaEditor validation on a dedicated Windows development or worker machine, configure:

```dotenv
MQL5_COMPILER_ENABLED=true
METAEDITOR_PATH=C:\Program Files\MetaTrader 5\metaeditor64.exe
MQL5_COMPILE_WORKDIR=./storage/compiler
MQL5_COMPILE_TIMEOUT_SECONDS=120
```

Leave compilation disabled on the web server. The adapter rejects DLL imports and non-allowlisted include paths, uses a per-generation workspace, records capped compiler output, and reports unavailable/failed/passed separately from AI and static validation.

## Docker setup

Copy `.env.example` to `.env`, then run:

```bat
dev.bat docker-up
```

The Docker stack starts Django, a single-concurrency Celery worker, and Redis. SQLite and Redis data are stored in named volumes. PostgreSQL replaces SQLite before production scaling.

## Useful commands

```bat
dev.bat web
dev.bat worker
dev.bat css-watch
dev.bat test
dev.bat check
dev.bat migrate
dev.bat migrations
dev.bat seed
dev.bat sync-ai
```

On Unix-like systems, equivalent Makefile targets are available through `make help`.

## Safety and trust

The included marketplace data is fictional and marked as demo content. Generated trading code is not financial advice. Backtest performance must always be shown with its assumptions, period, trade count, drawdown, and evidence status.
