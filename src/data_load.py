from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

def load_train_test(train_path=None, test_path=None):
    data_path = data_path or (DATA_DIR / "raw" / "tablon.parquet")
    
    if str(data_path).endswith(".csv"):
        data = pd.read_csv(data_path)
    else:
        data = pd.read_parquet(data_path)

    return data
