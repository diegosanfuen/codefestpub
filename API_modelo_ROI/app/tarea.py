"""tarea.py

EPO CodeFest style example
-------------------------
Minimal scheduled / background task example with structured logging.

Purpose in a CodeFest or demo context:
- Show how a task can be executed headlessly (cron, scheduler, worker).
- Produce an auditable log file with timestamps and severity levels.
- Keep configuration explicit and readable for reviewers.

Notes:
- `logging.basicConfig` should usually be called once at application startup.
  It is kept here for simplicity and self-containment of the example.
"""

import logging


def mi_tarea() -> None:
    """Execute a simple task and emit a log entry.

    This function represents a placeholder for any background job:
    data ingestion, model inference, report generation, etc.
    """

    # Configure logging.
    # In production, this is typically done at application entry-point level.
    logging.basicConfig(
        filename="Log/app.log",
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Log lifecycle information.
    # DEBUG / WARNING / ERROR examples are intentionally left commented
    # to keep the demo output clean.
    logging.info("Task executed successfully.")

    # --- Task business logic would go here ---
    # e.g. data processing, ML inference, API calls, etc.
    # -----------------------------------------


# Execute the task when the module is run directly.
# This makes the script usable both as:
# - an importable module
# - a standalone executable task
if __name__ == "__main__":
    mi_tarea()
