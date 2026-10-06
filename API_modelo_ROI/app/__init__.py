from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent      # .../app
MODEL_DIR = BASE_DIR / "modelos"               # .../app/modelos
MODEL_DIR.mkdir(parents=True, exist_ok=True)