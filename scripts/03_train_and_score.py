from src.io_utils import read_any, write_parquet
from src.model_baseline import train_baseline

TARGET = "target"  # <-- CAMBIA al nombre real del target en train

def main():
    train = read_any("data/processed/train_enriched.parquet")
    test  = read_any("data/processed/test_enriched.parquet")

    model = train_baseline(train, target_col=TARGET)

    X_test = test.copy()
    if hasattr(model[-1], "predict_proba"):
        score = model.predict_proba(X_test)[:, 1]
    else:
        score = model.predict(X_test)

    out = test.copy()
    out["score"] = score
    write_parquet(out, "data/processed/test_scored.parquet")
    print("OK: data/processed/test_scored.parquet")

if __name__ == "__main__":
    main()
