from pathlib import Path
from typing import List

import fastapi
import pandas as pd
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator

from challenge.model import DelayModel

app = fastapi.FastAPI()
model = DelayModel()

VALID_TIPOVUELO = {"I", "N"}
VALID_MES = set(range(1, 13))
VALID_OPERA: set = set()


@app.on_event("startup")
def train_model_on_startup() -> None:
    """Load the dataset and fit the model.

    Also populates VALID_OPERA with the airline names found in the training data for validation.
    """
    if model._model is not None:
        return
    data_path = Path(__file__).resolve().parent.parent / "data" / "data.csv"
    data = pd.read_csv(data_path)
    VALID_OPERA.update(data["OPERA"].dropna().unique())
    features, target = model.preprocess(data=data, target_column=model.TARGET_COL)
    model.fit(features=features, target=target)


class Flight(BaseModel):
    """One flight to score: airline (OPERA), flight type (TIPOVUELO), month (MES)."""

    OPERA: str
    TIPOVUELO: str
    MES: int

    @validator("TIPOVUELO")
    def _check_tipovuelo(cls, v: str) -> str:
        """Reject any TIPOVUELO outside {"I", "N"}."""
        if v not in VALID_TIPOVUELO:
            raise ValueError(f"TIPOVUELO must be one of {VALID_TIPOVUELO}")
        return v

    @validator("MES")
    def _check_mes(cls, v: int) -> int:
        """Reject any MES outside [1, 12]."""
        if v not in VALID_MES:
            raise ValueError("MES must be an integer in [1, 12]")
        return v

    @validator("OPERA")
    def _check_opera(cls, v: str) -> str:
        """Reject any OPERA not seen in the training data (VALID_OPERA is populated on startup)."""
        if VALID_OPERA and v not in VALID_OPERA:
            raise ValueError(f"OPERA {v} is not a known airline")
        return v


class PredictRequest(BaseModel):
    """A batch of flights to score in a single ``/predict`` call."""

    flights: List[Flight]


@app.exception_handler(RequestValidationError)
async def _validation_to_400(request, exc: RequestValidationError) -> JSONResponse:
    """Map Pydantic validation failures to HTTP 400."""
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


@app.get("/health", status_code=200)
async def get_health() -> dict:
    """Liveness probe — returns {"status": "OK"} once the process is up."""
    return {
        "status": "OK"
    }


@app.post("/predict", status_code=200)
async def post_predict(request: PredictRequest) -> dict:
    """Score a batch of flights and return one 0/1 delay prediction per flight.

    The list in "predict" is in the same order as the input "flights".
    """
    df = pd.DataFrame([flight.dict() for flight in request.flights])
    features = model.preprocess(data=df)
    predictions = model.predict(features=features)
    return {"predict": predictions}
