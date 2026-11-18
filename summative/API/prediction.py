from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

# Model configuration
MODEL_PATH = Path(__file__).resolve().parent / "best_model.pkl"
model_store = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Loading the trained pipeline once at startup
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found at: {MODEL_PATH}")
    model_store["pipeline"] = joblib.load(MODEL_PATH)
    print(f"Model loaded successfully from: {MODEL_PATH}")
    yield

    # Cleaning up resources on shutdown
    model_store.clear()

# FastAPI app and CORS configuration
app = FastAPI(
    title="Water Infrastructure Revenue Prediction API",
    description=("Predicts annual water revenue ($) from infrastructure, capacity, and demographic features."),
    version="1.0.0",
    lifespan=lifespan,
)

# Explict development origins to be updated with deployed URL
ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Pydantic Input and Output Schemas
class WaterPointInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "wp_type_cat": "Handpump",
                "wp_revenue_model": "waterpoint",
                "volume_method": None,
                "num_hh": 0.0,
                "num_taps": 0.0,
                "wp_pop_last": 1000.0,
                "wp_count_within_1000m": 15.0,
                "Population_Within_5000m": 46882.20448,
            }
        },
    )

    # categorical features (3)
    wp_type_cat: str = Field(
        ...,
        min_length=1,
        description="Water infrastructure type (e.g., Handpump, Scheme).",
    )

    wp_revenue_model: str = Field(
        ...,
        min_length=1,
        description="Revenue collection model.",
    )

    volume_method: Optional[str] = Field(
        default=None,
        description="Method used to measure water volume (nullable).",
    )

    # numerical features (5)
    num_hh: float = Field(
        ...,
        ge=0,
        allow_inf_nan=False,
        description="Number of households.",
    )

    num_taps: float = Field(
        ...,
        ge=0,
        allow_inf_nan=False,
        description="Number of water taps.",
    )

    wp_pop_last: float = Field(
        ...,
        ge=0,
        allow_inf_nan=False,
        description="Last recorded population served",
    )

    wp_count_within_1000m: float = Field(
        ...,
        ge=0,
        allow_inf_nan=False,
        description="Number of waterpoints within 1,000 metres.",
    )

    Population_Within_5000m: Optional[float] = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
        description="Population within 5,000 metres (nullable).",
    )

class PredictionResponse(BaseModel):
    predicted_annual_revenue: float =  Field(
        ...,
        description="Estimated annual water revenue in USD",
    )
    currency: str = "USD"

# API routes
@app.get("/", tags=["General"])
def read_root():
    return {
        "message": "Water Point Annual Revenue Prediction API",
        "docs_url": "/docs",
        "health_url": "/health",
        "predict_url": "/predict",
    }

@app.get("/health", tags=["Health"])
def health_check():
    if "pipeline" not in model_store:
        raise HTTPException(status_code=503, detail="Model pipeline is not loaded.")
    return  {
        "status": "healthy",
        "model_loaded": True,
        "model_path": MODEL_PATH.name,     
    }


@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
def predict_revenue(payload: WaterPointInput):
    pipeline = model_store.get("pipeline")

    if pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Model prediction is unavailable."
        )

    try:
        # Build a DataFrame from the validated input
        input_df = pd.DataFrame([payload.model_dump()])

        # Convert missing optional values to NaN
        input_df = input_df.replace({None: np.nan})

        # Match the original training feature order
        input_df = input_df[list(pipeline.feature_names_in_)]

        # Generate the prediction using the saved pipeline
        prediction = float(pipeline.predict(input_df)[0])

        # Ensure the returned value is finite
        if not np.isfinite(prediction):
            raise ValueError("Model produced a non-finite prediction.")

        estimated_revenue = round(prediction, 2)

        return PredictionResponse(
            predicted_annual_revenue=estimated_revenue
        )

    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=422,
            detail="Unable to process the supplied input."
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="An internal prediction error occurred."
        ) from exc
