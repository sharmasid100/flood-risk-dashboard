from __future__ import annotations

import os
import time
from dataclasses import asdict
from decimal import Decimal

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .demo_data import CITY_NAME, DATA_LABEL, generate_areas
from .engine import Intervention, MLFloodPredictor, RuleBasedFloodPredictor, recommend, simulate_intervention, snapshot_dict


app = FastAPI(
    title="DrainMind API",
    version="1.0.0",
    description="Flood-risk MVP using explicitly synthetic demonstration data.",
    root_path="/Prod"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

AREAS = generate_areas()
AREA_BY_ID = {area.area_id: area for area in AREAS}
SAGEMAKER_ENDPOINT = os.getenv("SAGEMAKER_ENDPOINT_NAME")
PREDICTOR = MLFloodPredictor(SAGEMAKER_ENDPOINT) if SAGEMAKER_ENDPOINT else RuleBasedFloodPredictor()
LOCAL_RAINFALL = {"local-demo": (0, 25.0)}


class RainfallRequest(BaseModel):
    rainfall_mm_hr: float = Field(ge=0, le=200)


class InterventionRequest(BaseModel):
    area_id: str
    intervention: Intervention
    rainfall_mm_hr: float | None = Field(default=None, ge=0, le=200)


def _area_dict(area):
    return asdict(area)


def _get_rainfall(simulation_id: str) -> float:
    table_name = os.getenv("SIMULATION_TABLE")
    if table_name:
        try:
            import boto3

            item = boto3.resource("dynamodb").Table(table_name).get_item(Key={"simulation_id": simulation_id}).get("Item", {})
            return float(item.get("rainfall_mm_hr", 25))
        except Exception as error:
            raise HTTPException(status_code=503, detail="Simulation state store is unavailable") from error
    return LOCAL_RAINFALL.get(simulation_id, (0, 25.0))[1]


def _set_rainfall(simulation_id: str, rainfall: float, revision: int) -> None:
    table_name = os.getenv("SIMULATION_TABLE")
    if table_name:
        try:
            import boto3

            boto3.resource("dynamodb").Table(table_name).update_item(
                Key={"simulation_id": simulation_id},
                UpdateExpression="SET #rain = :rain, #revision = :revision, #expires = :expires",
                ConditionExpression="attribute_not_exists(#revision) OR #revision <= :revision",
                ExpressionAttributeNames={"#rain": "rainfall_mm_hr", "#revision": "revision", "#expires": "expires_at"},
                ExpressionAttributeValues={
                    ":rain": Decimal(str(rainfall)),
                    ":revision": revision,
                    ":expires": int(time.time()) + 86400,
                },
            )
            return
        except Exception as error:
            from botocore.exceptions import ClientError

            if isinstance(error, ClientError) and error.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return
            raise HTTPException(status_code=503, detail="Simulation state store is unavailable") from error
    current_revision, _ = LOCAL_RAINFALL.get(simulation_id, (0, 25.0))
    if revision >= current_revision:
        LOCAL_RAINFALL[simulation_id] = (revision, rainfall)


def _snapshot(area, rainfall):
    return PREDICTOR.predict(area, rainfall)


def _risk_item(area, rainfall):
    return {**_area_dict(area), **snapshot_dict(_snapshot(area, rainfall))}


def _get_area(area_id: str):
    area = AREA_BY_ID.get(area_id)
    if area is None:
        raise HTTPException(status_code=404, detail="Area not found")
    return area


@app.get("/health")
def health():
    return {"status": "ok", "city": CITY_NAME, "data_label": DATA_LABEL}


@app.get("/api/areas")
def get_areas():
    return {"city": CITY_NAME, "data_label": DATA_LABEL, "areas": [_area_dict(area) for area in AREAS]}


@app.get("/api/weather")
def get_weather(simulation_id: str = Header(default="local-demo", alias="X-Simulation-Id")):
    return {
        "city": CITY_NAME,
        "data_label": DATA_LABEL,
        "timestamp": "Demo replay",
        "rainfall_mm_hr": _get_rainfall(simulation_id),
        "temperature_c": 28.4,
        "humidity_pct": 88,
        "observation_count": len(AREAS),
    }


@app.get("/api/risk")
def get_risk(simulation_id: str = Header(default="local-demo", alias="X-Simulation-Id")):
    rainfall = _get_rainfall(simulation_id)
    items = [_risk_item(area, rainfall) for area in AREAS]
    return {"city": CITY_NAME, "rainfall_mm_hr": rainfall, "data_label": DATA_LABEL, "areas": items}


@app.get("/api/risk/{area_id}")
def get_area_risk(area_id: str, simulation_id: str = Header(default="local-demo", alias="X-Simulation-Id")):
    return _risk_item(_get_area(area_id), _get_rainfall(simulation_id))


@app.get("/api/forecast/{area_id}")
def get_forecast(area_id: str, simulation_id: str = Header(default="local-demo", alias="X-Simulation-Id")):
    area = _get_area(area_id)
    rainfall = _get_rainfall(simulation_id)
    forecast = []
    for minutes, rainfall_delta in ((0, 0), (15, 8), (30, 16), (45, 24), (60, 28)):
        snapshot = PREDICTOR.predict(area, rainfall + rainfall_delta)
        forecast.append({"minute": minutes, "rainfall_mm_hr": snapshot.rainfall_mm_hr, "risk_score": snapshot.risk_score, "risk_level": snapshot.risk_level})
    return {"area_id": area_id, "data_label": DATA_LABEL, "forecast": forecast}


@app.post("/api/simulate/rainfall")
def simulate_rainfall(
    request: RainfallRequest,
    simulation_id: str = Header(default="local-demo", alias="X-Simulation-Id"),
    revision: int = Header(default=0, alias="X-Simulation-Revision", ge=0),
):
    _set_rainfall(simulation_id, request.rainfall_mm_hr, revision)
    return get_risk(simulation_id)


@app.post("/api/intervention/simulate")
def intervention_simulation(request: InterventionRequest, simulation_id: str = Header(default="local-demo", alias="X-Simulation-Id")):
    area = _get_area(request.area_id)
    rainfall = _get_rainfall(simulation_id) if request.rainfall_mm_hr is None else request.rainfall_mm_hr
    result = simulate_intervention(PREDICTOR, area, rainfall, request.intervention)
    if request.intervention == "emergency_warning":
        topic_arn = os.getenv("SNS_TOPIC_ARN")
        if os.getenv("ALERT_MODE", "local_demo") == "sns" and topic_arn:
            try:
                import boto3

                boto3.client("sns").publish(
                    TopicArn=topic_arn,
                    Subject=f"DrainMind flood warning: {area.name}",
                    Message=f"Flood risk alert: {area.name} is expected to experience severe waterlogging within about {result['before']['time_to_flood_minutes']} minutes. This is a modeled demonstration alert.",
                )
                result["notification"] = {"mode": "sns", "sent": True, "message": "SNS topic notification sent."}
            except Exception as error:
                raise HTTPException(status_code=503, detail="SNS notification could not be sent") from error
        else:
            result["notification"] = {"mode": "local_demo", "sent": False, "message": "In-app demonstration only. No SMS was sent."}
    return result


@app.get("/api/recommendations/{area_id}")
def get_recommendations(area_id: str, simulation_id: str = Header(default="local-demo", alias="X-Simulation-Id")):
    area = _get_area(area_id)
    snapshot = _snapshot(area, _get_rainfall(simulation_id))
    return {"area_id": area_id, "recommendations": recommend(area, snapshot)}


@app.get("/api/dashboard/summary")
def get_summary(simulation_id: str = Header(default="local-demo", alias="X-Simulation-Id")):
    rainfall = _get_rainfall(simulation_id)
    items = [_risk_item(area, rainfall) for area in AREAS]
    high_risk = [item for item in items if item["risk_score"] >= 51]
    critical = [item for item in items if item["risk_score"] >= 76]
    next_event = min(high_risk, key=lambda item: item["time_to_flood_minutes"], default=None)
    return {
        "city": CITY_NAME,
        "data_label": DATA_LABEL,
        "rainfall_mm_hr": rainfall,
        "area_count": len(AREAS),
        "high_risk_areas": len(high_risk),
        "critical_areas": len(critical),
        "next_event": None if next_event is None else {
            "area_id": next_event["area_id"],
            "area_name": next_event["name"],
            "minutes": next_event["time_to_flood_minutes"],
        },
        "population_at_risk": sum(item["population"] for item in high_risk),
    }


try:
    from mangum import Mangum

    handler = Mangum(app)
except ImportError:
    handler = None