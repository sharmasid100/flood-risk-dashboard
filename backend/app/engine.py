from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from typing import Any, Literal


Intervention = Literal[
    "clear_drain",
    "deploy_pump",
    "restrict_traffic",
    "emergency_warning",
    "open_water_storage",
]


@dataclass(frozen=True)
class Area:
    area_id: str
    name: str
    x: float
    y: float
    elevation_m: float
    drain_capacity_mm_hr: float
    impervious_surface_pct: float
    drainage_score: float
    historical_flood_frequency: float
    population: int
    near_major_road: bool


@dataclass(frozen=True)
class RiskSnapshot:
    area_id: str
    risk_score: int
    risk_level: str
    rainfall_mm_hr: float
    severity: int
    time_to_flood_minutes: int
    factors: dict[str, float]


DEFAULT_WEIGHTS = {
    "rainfall": 0.35,
    "drainage": 0.25,
    "elevation": 0.15,
    "impervious": 0.15,
    "historical": 0.10,
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class FloodPredictor:
    def predict(self, area: Area, rainfall_mm_hr: float) -> RiskSnapshot:
        raise NotImplementedError


class RuleBasedFloodPredictor(FloodPredictor):
    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = dict(weights or DEFAULT_WEIGHTS)
        if set(self.weights) != set(DEFAULT_WEIGHTS):
            raise ValueError("Weights must define rainfall, drainage, elevation, impervious, and historical")
        if any(value < 0 for value in self.weights.values()) or sum(self.weights.values()) <= 0:
            raise ValueError("Weights must be non-negative and have a positive total")
        total = sum(self.weights.values())
        self.weights = {key: value / total for key, value in self.weights.items()}

    def predict(self, area: Area, rainfall_mm_hr: float) -> RiskSnapshot:
        rainfall = max(0.0, rainfall_mm_hr)
        capacity = max(1.0, area.drain_capacity_mm_hr)
        drainage_stress = _clamp((rainfall / capacity - 0.35) / 1.8)
        factors = {
            "rainfall": _clamp(rainfall / 90),
            "drainage": _clamp(0.68 * drainage_stress + 0.32 * (1 - area.drainage_score)),
            "elevation": _clamp((24 - area.elevation_m) / 24),
            "impervious": _clamp(area.impervious_surface_pct / 100),
            "historical": _clamp(area.historical_flood_frequency),
        }
        score = round(100 * sum(self.weights[key] * factors[key] for key in self.weights))
        score = max(0, min(100, score))
        level = "LOW" if score <= 25 else "MODERATE" if score <= 50 else "HIGH" if score <= 75 else "CRITICAL"
        vulnerability = _clamp(0.55 * area.historical_flood_frequency + 0.45 * (1 - area.drainage_score))
        margin = capacity - rainfall
        if margin >= 0:
            minutes = 18 + margin * 0.55 * (1 - vulnerability)
        else:
            minutes = 8 + 34 / (1 + abs(margin) / capacity) * (1 - 0.55 * vulnerability)
        return RiskSnapshot(
            area_id=area.area_id,
            risk_score=score,
            risk_level=level,
            rainfall_mm_hr=round(rainfall, 1),
            severity=round(100 * _clamp((score / 100) ** 1.15)),
            time_to_flood_minutes=max(5, round(minutes)),
            factors={key: round(value, 3) for key, value in factors.items()},
        )


class MLFloodPredictor(FloodPredictor):
    """Adapter for a SageMaker endpoint serving a RandomForest predictor."""

    def __init__(self, endpoint_name: str, runtime_client: Any = None) -> None:
        if not endpoint_name:
            raise ValueError("A SageMaker endpoint name is required")
        self.endpoint_name = endpoint_name
        self.runtime_client = runtime_client

    def predict(self, area: Area, rainfall_mm_hr: float) -> RiskSnapshot:
        runtime_client = self.runtime_client
        if runtime_client is None:
            import boto3

            runtime_client = boto3.client("sagemaker-runtime")
        features = asdict(area)
        features["rainfall_mm_hr"] = max(0.0, rainfall_mm_hr)
        response = runtime_client.invoke_endpoint(
            EndpointName=self.endpoint_name,
            ContentType="application/json",
            Body=json.dumps({"features": features}).encode("utf-8"),
        )
        prediction = json.loads(response["Body"].read())
        score = max(0, min(100, round(float(prediction["risk_score"]))))
        level = "LOW" if score <= 25 else "MODERATE" if score <= 50 else "HIGH" if score <= 75 else "CRITICAL"
        return RiskSnapshot(
            area_id=area.area_id,
            risk_score=score,
            risk_level=level,
            rainfall_mm_hr=round(max(0.0, rainfall_mm_hr), 1),
            severity=round(float(prediction.get("severity", score))),
            time_to_flood_minutes=max(5, round(float(prediction["time_to_flood_minutes"]))),
            factors={key: round(float(value), 3) for key, value in prediction.get("factors", {}).items()},
        )


def snapshot_dict(snapshot: RiskSnapshot) -> dict[str, object]:
    return asdict(snapshot)


def recommend(area: Area, snapshot: RiskSnapshot) -> list[dict[str, str]]:
    choices: list[dict[str, str]] = []
    if snapshot.rainfall_mm_hr >= area.drain_capacity_mm_hr * 0.75:
        choices.append({"id": "clear_drain", "label": "Clear drain", "reason": "Rainfall is approaching this area's drainage capacity."})
    if snapshot.rainfall_mm_hr >= 65 and snapshot.risk_score >= 65:
        choices.append({"id": "deploy_pump", "label": "Deploy pump", "reason": "Extreme rainfall is likely to overwhelm passive drainage."})
    if area.near_major_road and snapshot.risk_score >= 55:
        choices.append({"id": "restrict_traffic", "label": "Restrict traffic", "reason": "This high-risk area borders a major road corridor."})
    choices.append({"id": "emergency_warning", "label": "Issue warning", "reason": "A local warning gives people time to avoid exposed streets."})
    choices.append({"id": "open_water_storage", "label": "Open water storage", "reason": "Temporary storage can reduce runoff reaching the drainage network."})
    return choices[:3]


def simulate_intervention(
    predictor: FloodPredictor,
    area: Area,
    rainfall_mm_hr: float,
    intervention: Intervention,
    pump_capacity_mm_hr: float = 24,
) -> dict[str, object]:
    before = predictor.predict(area, rainfall_mm_hr)
    adjusted_area = area
    adjusted_rainfall = rainfall_mm_hr
    if intervention == "clear_drain":
        adjusted_area = replace(area, drain_capacity_mm_hr=area.drain_capacity_mm_hr * 1.25)
    elif intervention == "deploy_pump":
        adjusted_area = replace(area, drain_capacity_mm_hr=area.drain_capacity_mm_hr + max(0, pump_capacity_mm_hr))
    elif intervention == "restrict_traffic":
        adjusted_area = replace(area, impervious_surface_pct=max(0, area.impervious_surface_pct - 8))
    elif intervention == "open_water_storage":
        adjusted_rainfall = rainfall_mm_hr * 0.84
    elif intervention != "emergency_warning":
        raise ValueError(f"Unknown intervention: {intervention}")
    after = predictor.predict(adjusted_area, adjusted_rainfall)
    risk_reduction = max(0, round((before.risk_score - after.risk_score) / max(1, before.risk_score) * 100))
    severity_reduction = max(0, round((before.severity - after.severity) / max(1, before.severity) * 100))
    return {
        "intervention": intervention,
        "label": intervention.replace("_", " ").title(),
        "simulation_only": True,
        "before": snapshot_dict(before),
        "after": snapshot_dict(after),
        "impact": {
            "risk_reduction_pct": risk_reduction,
            "severity_reduction_pct": severity_reduction,
            "extra_warning_time_minutes": max(0, after.time_to_flood_minutes - before.time_to_flood_minutes),
            "exposure_reduction_pct": 35 if intervention == "emergency_warning" else 0,
        },
    }