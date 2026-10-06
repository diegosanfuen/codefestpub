import pandas as pd
import numpy as np

def priority_complexity(n):
    if pd.isna(n):
        return np.nan
    if n <= 1:
        return "simple"
    if n <= 3:
        return "medium"
    return "complex"

