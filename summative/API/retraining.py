
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# Paths and configuration
API_DIR = Path(__file__).resolve().parent

DATA_DIR = API_DIR / "data"
MODEL_PATH = API_DIR / "best_model.pkl"
TRAINING_DATA_PATH = DATA_DIR / "training_data.csv"
CANDIDATE_PATH = API_DIR / "candidate_model.pkl"

TARGET = "wp_revenue_USD"

NUMERIC_FEATURES = [
    "num_hh",
    "num_taps",
    "wp_pop_last",
    "wp_count_within_1000m",
    "Population_Within_5000m",
]

CATEGORICAL_FEATURES = [
    "wp_type_cat",
    "wp_revenue_model",
    "volume_method",
]


# Dataset validation
def validate_new_data(
    new_data: pd.DataFrame,
    expected_columns: list[str]
) -> pd.DataFrame:

    if set(new_data.columns) != set(expected_columns):
        raise ValueError(
            "New data must contain exactly the eight "
            "input features and wp_revenue_USD."
        )

    if len(new_data) < 50:
        raise ValueError(
            "At least 50 new labeled observations are "
            "required for this retraining workflow."
        )

    data = new_data[expected_columns].copy()

    # Validate numeric predictors
    for column in NUMERIC_FEATURES:
        data[column] = pd.to_numeric(
            data[column], errors="raise"
        )

        values = data[column].dropna()

        if not np.isfinite(values).all():
            raise ValueError(
                f"{column} contains non-finite values."
            )

        if (values < 0).any():
            raise ValueError(
                f"{column} cannot contain negative values."
            )

        if (
            column != "Population_Within_5000m"
            and data[column].isna().any()
        ):
            raise ValueError(
                f"{column} cannot contain missing values."
            )

    # Validate required categorical predictors
    for column in ["wp_type_cat"]:
        if (
            data[column].isna().any()
            or data[column].astype(str).str.strip().eq("").any()
        ):
            raise ValueError(
                f"{column} must contain non-empty values."
            )

    # Missing values in these columns are handled by the pipeline's imputer.
    for column in ["wp_revenue_model", "volume_method"]:
        invalid_blank = (
            data[column].notna()
            & data[column].astype(str).str.strip().eq("")
        )

        if invalid_blank.any():
            raise ValueError(
                f"{column} cannot be an empty string."
            )

    # Validate the target variable
    data[TARGET] = pd.to_numeric(
        data[TARGET], errors="raise"
    )

    if (
        data[TARGET].isna().any()
        or not np.isfinite(data[TARGET]).all()
        or (data[TARGET] < 0).any()
    ):
        raise ValueError(
            "Annual revenue must be finite, non-null "
            "and non-negative."
        )

    return data


# Model retraining
def retrain_model(new_data_path: Path) -> dict:

    # Load historical training data and new observations
    original_data = pd.read_csv(TRAINING_DATA_PATH)
    new_data = pd.read_csv(new_data_path)

    # Validate using the expected original columns
    expected_columns = original_data.columns.tolist()

    new_data = validate_new_data(
        new_data,
        expected_columns
    )

    # Preserve distinct observations even when all nine values match.
    # These CSVs have no observation IDs, so values cannot establish identity.
    # The caller must supply genuinely new observations; the demonstration
    # batch is separated by original row index in the notebook. Repeated
    # ingestion would require persistent observation IDs or a batch registry.

    # Split new data before combining with historical data
    new_train, new_validation = train_test_split(
        new_data,
        test_size=0.2,
        random_state=42
    )

    # Combine historical and new training observations
    combined_training = pd.concat(
        [original_data, new_train],
        ignore_index=True
    )

    X_train = combined_training.drop(columns=[TARGET])
    y_train = combined_training[TARGET]

    X_validation = new_validation.drop(columns=[TARGET])
    y_validation = new_validation[TARGET]

    # Load the existing pipeline
    current_pipeline = joblib.load(MODEL_PATH)

    # Create an unfitted copy with the same configuration
    candidate_pipeline = clone(current_pipeline)

    # Fit preprocessing and Random Forest on combined data
    candidate_pipeline.fit(X_train, y_train)

    # Evaluate both models on identical validation records
    current_predictions = current_pipeline.predict(
        X_validation
    )

    candidate_predictions = candidate_pipeline.predict(
        X_validation
    )

    current_mse = mean_squared_error(
        y_validation, current_predictions
    )

    candidate_mse = mean_squared_error(
        y_validation, candidate_predictions
    )

    candidate_mae = mean_absolute_error(
        y_validation, candidate_predictions
    )

    candidate_r2 = r2_score(
        y_validation, candidate_predictions
    )

    # Check whether candidate improves validation MSE
    improved = candidate_mse < current_mse

    # Save candidate separately
    # Never overwrite the deployed model here
    joblib.dump(candidate_pipeline, CANDIDATE_PATH)

    return {
        "status": "candidate_evaluated",
        "new_observations": len(new_data),
        "total_training_observations": len(combined_training),
        "validation_observations": len(new_validation),
        "current_model_mse": round(float(current_mse), 4),
        "candidate_model_mse": round(float(candidate_mse), 4),
        "candidate_model_mae": round(float(candidate_mae), 4),
        "candidate_model_r2": round(float(candidate_r2), 4),
        "candidate_improved": bool(improved),
        "production_model_unchanged": True,
    }
