"""task_mngr.py

EPO CodeFest style example
-------------------------
Lightweight task scheduler / time worker based on the `schedule` library.

Why this file exists in a demo or hackathon context:
- Demonstrates how to orchestrate periodic background tasks without heavy frameworks.
- Keeps scheduling logic explicit and readable for reviewers.
- Runs safely in the background using a daemon thread.

Typical use cases:
- Periodic data ingestion
- Scheduled model inference
- Health checks or report generation
"""

import sys
import time
import threading

import schedule
import tarea


# Optional: extend Python path for local / containerized environments.
# This is often needed in research or demo setups where code is mounted
# from external volumes.
sys.path.append("/opt/conda/workdir/AEAT/Esqueleto_Definitivo_Pruebas")


def ejecutar_tarea() -> None:
    """Wrapper function to execute the scheduled task.

    Keeping this as a thin wrapper makes it easy to:
    - swap the task implementation
    - add logging, metrics, or exception handling later
    """
    tarea.mi_tarea()


def iniciar_timeworker() -> None:
    """Initialize and start the background scheduler.

    Behaviour:
    - Schedule the task to run periodically.
    - Execute the task once immediately at startup.
    - Run the scheduler loop in a daemon thread so it does not
      block the main application lifecycle.
    """

    # Schedule the task (example: every 1 minute).
    # Adjust the interval as needed for the demo.
    schedule.every(1).minutes.do(ejecutar_tarea)

    # Run once at startup (useful for smoke tests and demos).
    ejecutar_tarea()

    def run_schedule() -> None:
        """Internal scheduler loop.

        This loop checks for pending jobs and executes them.
        It runs indefinitely in a background thread.
        """
        while True:
            schedule.run_pending()
            time.sleep(1)

    # Start the scheduler in a daemon thread.
    threading.Thread(target=run_schedule, daemon=True).start()


if __name__ == "__main__":
    # Start the time worker.
    iniciar_timeworker()

    # Keep the main process alive.
    # In containerized environments, this prevents the container from exiting.
    while True:
        time.sleep(1)
