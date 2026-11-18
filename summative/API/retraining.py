
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# File locations
API_DIR = Path(__file__).resolve().parent

MODEL_PATH = API_DIR / "best_model.pkl"
TRAINING_DATA_PATH = API_DIR / "training_data.csv"
CANDIDATE_MODEL_PATH = API_DIR / "candidate_model.pkl"

TARGET = "wp_revenue_USD"


def retrain_model(new_data_path: Path) -> dict:
    # Training and evaluating a candidate using newly labeled observations

    # Loading the original training data and new observations
    training_data = pd.read_csv(TRAINING_DATA_PATH)
    new_data = pd.read_csv(new_data_path)

    # Verifying the expected dataset structure
    required_columns = set(training_data.columns)

    if set(new_data.columns) != required_columns:
        raise ValueError(
            "New data must contain exactly the eight input "
            "features and wp_revenue_USD."
        )

    if len(new_data) < 20:
        raise ValueError(
            "At least 20 new labeled observations are required."
        )

    # Checking the target values
    revenue = pd.to_numeric(new_data[TARGET], errors="raise")

    if revenue.isna().any() or not np.isfinite(revenue).all():
        raise ValueError("Revenue values must be finite and non-null.")

    if (revenue < 0).any():
        raise ValueError("Annual revenue cannot be negative.")

    new_data[TARGET] = revenue

    # Splitting new observations into training and validation subsets
    new_train, new_val = train_test_split(
        new_data,
        test_size=0.2,
        random_state=42
    )

    # Combining existing training data with new training records
    combined_train = pd.concat(
        [training_data, new_train],
        ignore_index=True
    )

    X_train_new = combined_train.drop(columns=[TARGET])
    y_train_new = combined_train[TARGET]

    X_val_new = new_val.drop(columns=[TARGET])
    y_val_new = new_val[TARGET]

    # Loading the currently deployed pipeline
    current_pipeline = joblib.load(MODEL_PATH)

    # Cloning to create an unfitted pipeline with identical settings
    candidate_pipeline = clone(current_pipeline)

    # Training the candidate from scratch
    candidate_pipeline.fit(X_train_new, y_train_new)

    # Evaluating both models on the SAME validation observations
    current_preds = current_pipeline.predict(X_val_new)
    candidate_preds = candidate_pipeline.predict(X_val_new)

    current_mse = mean_squared_error(y_val_new, current_preds)
    candidate_mse = mean_squared_error(y_val_new, candidate_preds)

    candidate_r2 = r2_score(y_val_new, candidate_preds)

    # Saving candidate separately; leaving production model unchanged
    joblib.dump(candidate_pipeline, CANDIDATE_MODEL_PATH)

    return {
        "new_observations": len(new_data),
        "training_observations": len(combined_train),
        "validation_observations": len(new_val),
        "current_model_mse": round(float(current_mse), 4),
        "candidate_model_mse": round(float(candidate_mse), 4),
        "candidate_model_r2": round(float(candidate_r2), 4),
        "candidate_improved": bool(candidate_mse < current_mse),
        "candidate_path": str(CANDIDATE_MODEL_PATH),
    }
