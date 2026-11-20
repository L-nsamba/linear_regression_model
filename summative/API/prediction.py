from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

import os
import hmac
import tempfile
import threading

from fastapi import File, Header, UploadFile

import hashlib
import json

# Helpful to render and allowes running API as both API.prediction:app and prediction:app
try:
    from .retrain import retrain_model, promote_candidate
except ImportError:
    from retrain import retrain_model, promote_candidate

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

# Allow browser requests only from explicitly trusted development origins.
# Restrict methods and headers to those needed by the API.
# Credentials are disabled because the application does not use
# browser cookies or authenticated browser sessions.
# Flutter mobile requests are not subject to browser CORS enforcement.
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
    allow_headers=["Content-Type", "Authorization", "X-Admin-Key"],
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

    wp_revenue_model: Optional[str] = Field(
        default=None,
        description="Revenue collection model (nullable).",
    )

    volume_method: Optional[str] = Field(
        default=None,
        description="Method used to measure water volume (nullable).",
    )

    # numerical features (5)
    num_hh: float = Field(
        ...,
        ge=0,
        le=1000,
        allow_inf_nan=False,
        description="Number of households (0-1000).",
    )

    num_taps: float = Field(
        ...,
        ge=0,
        le=50,
        allow_inf_nan=False,
        description="Number of water taps (0-50).",
    )

    wp_pop_last: float = Field(
        ...,
        ge=0,
        le=25000,
        allow_inf_nan=False,
        description="Last recorded population served (0-25000).",
    )

    wp_count_within_1000m: float = Field(
        ...,
        ge=0,
        le=70,
        allow_inf_nan=False,
        description="Number of waterpoints within 1,000 metres (0-70).",
    )

    Population_Within_5000m: Optional[float] = Field(
        default=None,
        ge=0,
        le=850000,
        allow_inf_nan=False,
        description="Population within 5,000 metres (0-850000; nullable).",
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

# Preventing overlapping retraining calls in this API process
retraining_lock = threading.Lock()

# Protection against repeatedly presenting retraining_batch.csv as new data
BATCH_REGISTRY_PATH = MODEL_PATH.parent / "processed_batches.json"

@app.post("/retrain", tags=["Model Management"])
def trigger_retraining(
    file: UploadFile = File(...),
    x_admin_key: str | None = Header(default=None),
):

    # Verifying administrator authorization
    expected_key = os.getenv("RETRAIN_API_KEY")

    if not expected_key:
        raise HTTPException(
            status_code=503,
            detail="Retraining is not configured."
        )

    if not x_admin_key or not hmac.compare_digest(
        x_admin_key, expected_key
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid administrator key"
        )

    # Validating file type
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV uploads are supported"
        )

    # Preventing simultaneous retraining requests
    if not retraining_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Another retraining job is already running."
        )

    temp_path = None

    try:
        # Limit uploads to 5MB
        max_size = 5 * 1024 * 1024
        contents = file.file.read(max_size + 1)

        if len(contents) > max_size:
            raise HTTPException(
                status_code=413,
                detail="Uploaded CSV exceeds 5MB"
            )

        # Identifying the uploaded batch
        batch_id = hashlib.sha256(contents).hexdigest()

        # Checking previously promoted batches
        processed_batches = set()

        if BATCH_REGISTRY_PATH.exists():
            processed_batches = set(
                json.loads(
                    BATCH_REGISTRY_PATH.read_text(
                        encoding="utf-8"
                    )
                )
            )

        if batch_id in processed_batches:
            raise HTTPException(
                status_code=409,
                detail="This batch has already been processed."
            )

        # Saving the upload temporarily
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".csv",
            delete=False
        ) as temp_file:
            temp_file.write(contents)
            temp_path = Path(temp_file.name)

        # Executing the existing retraining workflow
        results = retrain_model(temp_path)

        # Not promoting a candidate that failed validation
        if not results["candidate_improved"]:
            return {
                "message": (
                    "Retraining completed, but the candidate "
                    "did not improve validation MSE."
                ),
                "model_updated": False,
                "results": results,
            }

        # Promoting and loading the updated model
        updated_pipeline = promote_candidate()

        # Ensuring subsequent predictions use the new pipeline
        model_store["pipeline"] = updated_pipeline

        # Recording the successfully promoted batch
        processed_batches.add(batch_id)

        registry_temp = BATCH_REGISTRY_PATH.with_suffix(".tmp")
        registry_temp.write_text(
            json.dumps(sorted(processed_batches), indent=2),
            encoding="utf-8"
        )
        os.replace(registry_temp, BATCH_REGISTRY_PATH)

        return {
            "message": "Model retrained and activated successfully.",
            "model_updated": True,
            "results": {
                **results,
                "production_model_unchanged": False,
            },
        }

    except HTTPException:
        raise

    except(ValueError, pd.errors.ParserError) as exc:
        raise HTTPException(
            status_code=422,
            detail="Invalid retraining dataset"
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Retraining or model activation failed."
        ) from exc

    finally:
        try:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
        finally:
            try:
                file.file.close()
            finally:
                retraining_lock.release()
