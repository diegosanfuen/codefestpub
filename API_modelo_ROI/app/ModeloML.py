"""modelo_ml.py

EPO CodeFest style notes
------------------------
This module provides a small, dependency-light wrapper around a scikit-learn–like
estimator (anything that exposes `.fit()` and `.predict()`).

Why this exists in a CodeFest demo:
- Keep the API surface tiny and readable for evaluators.
- Capture input schema (`X.dtypes` / target type) at training time so you can
  validate inference payloads later in the pipeline (API, batch scoring, etc.).
- Offer a single, explicit serialization entry-point (pickle), which is often
  enough for a hackathon/demo.

Security note:
Pickle can execute arbitrary code when loading. Only load model files you trust.
"""

from __future__ import annotations

import pickle
from typing import Any, Optional, Union

import numpy as np
import pandas as pd


class ModeloML:
    """A thin wrapper for ML estimators.

    Parameters
    ----------
    modelo:
        A fitted/unfitted estimator implementing:
        - fit(X, y)
        - predict(X)
    """

    def __init__(self, modelo: Any):
        self.modelo = modelo
        # Stored during training to document / validate expected inputs at inference time.
        self.esquema_X: Optional[pd.Series] = None
        self.esquema_y: Optional[Any] = None

    def establecer_datasets(self, X: pd.DataFrame, y: Any) -> None:
        """Store the schema (dtypes) of training inputs and target.

        This is intentionally lightweight: we keep dtypes rather than full
        statistics. In a production pipeline you might also store:
        - feature ordering
        - missing-value policy
        - categorical vocabularies / encoders
        - training metadata (date, code version, dataset hash, etc.)

        Parameters
        ----------
        X:
            Training feature matrix as a pandas DataFrame.
        y:
            Training target. Supported common cases:
            - pandas DataFrame / Series
            - Python list
            - numpy array
        """
        # Pandas dtypes are a convenient compact representation of "what we trained with".
        self.esquema_X = X.dtypes

        # Target (`y`) can come in different shapes depending on the training code.
        if isinstance(y, pd.DataFrame):
            self.esquema_y = y.dtypes
        elif isinstance(y, list):
            # Keep the type of the first element as a quick hint (classification labels, floats, etc.)
            self.esquema_y = type(y[0]) if y else None
        else:
            # numpy arrays / pandas Series typically expose `.dtype`
            self.esquema_y = str(getattr(y, "dtype", type(y)))

    def entrenar(self, X_train: pd.DataFrame, y_train: Any) -> None:
        """Fit the underlying estimator and persist training schema."""
        self.modelo.fit(X_train, y_train)
        self.establecer_datasets(X_train, y_train)

    def predecir(self, X_test: pd.DataFrame) -> Any:
        """Run inference using the underlying estimator."""
        return self.modelo.predict(X_test)

    def guardar_modelo(self, ruta_archivo: str) -> None:
        """Serialize the underlying estimator to disk via pickle.

        Notes
        -----
        - This stores only `self.modelo` (the estimator), not this wrapper.
          That keeps compatibility with other tooling expecting a raw estimator.
        - If you want to persist schema too, you can pickle the wrapper instead.
        """
        with open(ruta_archivo, "wb") as archivo:
            pickle.dump(self.modelo, archivo)

    def esquema_entrada(self) -> pd.DataFrame:
        """Return the input schema as a DataFrame (feature dtype per column)."""
        if self.esquema_X is None:
            # Fail fast: schema is defined after training (or can be set manually).
            raise ValueError("Input schema is not set. Train the model or call `establecer_datasets()` first.")
        return pd.DataFrame(self.esquema_X, columns=["tipo_de_dato"])

    @staticmethod
    def cargar_modelo(ruta_archivo: str) -> "ModeloML":
        """Load a pickled estimator and wrap it in `ModeloML`.

        Security note:
        Only load files from trusted sources.
        """
        with open(ruta_archivo, "rb") as archivo:
            try:
                modelo_cargado = pickle.load(archivo)
            except Exception as e:
                # Re-raise with context, preserving the original message.
                raise Exception(e)
        return ModeloML(modelo_cargado)
