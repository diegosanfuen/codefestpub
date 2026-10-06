import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, accuracy_score
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression

def train_baseline(df, target_col):
    y = df[target_col].values
    X = df.drop(columns=[target_col])

    num_cols = X.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = [c for c in X.columns if c not in num_cols]

    pre = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median"))]), num_cols),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("oh", OneHotEncoder(handle_unknown="ignore"))]), cat_cols),
    ])

    clf = LogisticRegression(max_iter=300, n_jobs=-1)

    pipe = Pipeline([("pre", pre), ("clf", clf)])
    Xtr, Xva, ytr, yva = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y if len(set(y))<20 else None)

    pipe.fit(Xtr, ytr)

    if len(set(y)) == 2:
        p = pipe.predict_proba(Xva)[:, 1]
        auc = roc_auc_score(yva, p)
        print("AUC:", auc)
    pred = pipe.predict(Xva)
    print("ACC:", accuracy_score(yva, pred))
    return pipe
