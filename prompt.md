# DrainMind — MVP Master Prompt (AWS Edition)

## 1. Project Overview

Build **DrainMind**, an AI-powered, cloud-native hyperlocal flood and waterlogging prediction system for cities.

The core idea is:

> **Don't wait for a street to flood. Predict where flooding will happen, when it will happen, and what action can reduce its impact.**

DrainMind is an MVP for a hackathon. It should demonstrate a complete end-to-end pipeline leveraging cloud infrastructure:

**Data → Prediction (AWS) → Risk Map → Early Warning (Amazon SNS) → Recommended Intervention → Impact Simulation**

The MVP should be visually impressive, technically credible, and ideally deployed on AWS to demonstrate scalability. 

Do NOT build an overly complex production system. Focus on a polished working prototype with simulated/replayed data where real-time data is unavailable.

---

## 2. Problem Statement

Urban flooding and monsoon waterlogging often become visible only after roads are already unusable.

DrainMind aims to provide an early warning system that predicts:
- Which areas are likely to experience waterlogging
- How severe the flooding may become
- Approximately when flooding may begin
- Which locations should receive intervention first

The system should ultimately answer:
> **What is going to flood, when, and what should we do about it?**

---

## 3. MVP Goal

Build a web-based dashboard for a selected demo city/area.

The MVP must allow a user to:
1. View the city on an interactive map.
2. View current rainfall and waterlogging conditions.
3. Simulate increasing rainfall.
4. Generate flood-risk predictions.
5. Display predicted high-risk locations on the map.
6. Show predicted time-to-flood.
7. Select a high-risk location.
8. View the likely cause/risk factors.
9. Receive recommended interventions.
10. Simulate an intervention and compare:
    - flood severity without intervention
    - flood severity with intervention
11. Display the estimated impact of the intervention.

---

## 4. Core MVP Scenario

The main demo should be:

### Scenario
A heavy rainfall event begins. The user increases rainfall intensity using a slider.

Example:
```text
Rainfall:
10 mm/hr → 25 mm/hr → 50 mm/hr → 80 mm/hr
```

As rainfall increases, DrainMind dynamically updates flood risk.

Example:
```text
Area A
Risk: LOW → MEDIUM → HIGH → CRITICAL

Area B
Risk: LOW → LOW → MEDIUM → HIGH

Area C
Risk: MEDIUM → HIGH → CRITICAL
```

The map should visually communicate this transition. Then DrainMind should display:

> **Critical flood risk predicted in Area C within 32 minutes.**

The system should recommend:
> Clear drainage channel  
> Deploy temporary pump  
> Restrict traffic  
> Issue local warning

The user selects an intervention. DrainMind then simulates:

```text
Without intervention:
Flood severity = 82

With intervention:
Flood severity = 31

Estimated reduction = 62%
```

This is the key demonstration.

---

## 5. AWS System Architecture

Use a modern, serverless cloud architecture tailored for rapid hackathon deployment:

```text
Frontend Dashboard
React + TypeScript (Hosted on AWS Amplify)
        ↓
API Layer
Amazon API Gateway
        ↓
Compute Engine
AWS Lambda (Python/FastAPI) or AWS App Runner
        ↓
Prediction / Intervention Logic
(Python core)
        ↓
Database
Amazon RDS (PostgreSQL) or Amazon DynamoDB
        ↓
Alerts & Notifications
Amazon SNS (Simple Notification Service)
```

Use a clean service-oriented structure so cloud components can interact smoothly.

---

## 6. Recommended Tech Stack

### Frontend
- React + TypeScript
- Vite
- **AWS Amplify** (for seamless CI/CD hosting)
- Tailwind CSS
- Leaflet or Mapbox for maps
- Recharts for graphs

*Prefer dark/light professional environmental-dashboard styling.*

### Backend
- Python
- FastAPI (wrapped in Mangum for AWS Lambda compatibility)
- **AWS Lambda** & **Amazon API Gateway** (Serverless backend)
- Pydantic, NumPy, Pandas

### Database
- **Amazon RDS (PostgreSQL)** for relational data (areas, history, predictions).
- *(Alternative for speed)*: **Amazon DynamoDB** for fast read/write of real-time simulation states.

### Cloud Services
- **Amazon SNS**: For dispatching SMS/Email alerts when a critical threshold is met.
- **Amazon SageMaker** *(Optional/Future)*: For hosting ML models.

---

## 7. Data Model

Each geographic area should have information similar to:

```json
{
  "area_id": "A001",
  "name": "Central Market",
  "latitude": 10.123,
  "longitude": 76.456,
  "elevation_m": 12.5,
  "drain_capacity_mm_hr": 45,
  "impervious_surface_pct": 78,
  "drainage_score": 0.62,
  "historical_flood_frequency": 0.71
}
```

Weather/rainfall observation:

```json
{
  "timestamp": "2026-10-08T12:00:00",
  "area_id": "A001",
  "rainfall_mm_hr": 62,
  "temperature_c": 29,
  "humidity_pct": 91
}
```

Historical event:

```json
{
  "area_id": "A001",
  "rainfall_mm_hr": 75,
  "duration_minutes": 60,
  "flood_severity": 0.84,
  "flood_duration_minutes": 95
}
```

---

## 8. Flood Risk Model

For the MVP, do NOT pretend to have a scientifically validated hydrological model. Use a transparent hybrid approach.

Create a **Flood Risk Score** between 0 and 100.

Possible features:
- current rainfall
- rainfall accumulation
- rainfall intensity
- drainage capacity
- elevation
- impervious surface
- historical flood frequency
- drainage score

Example conceptual formula:

```text
Rainfall Risk + Drainage Stress + Terrain Risk + Historical Risk + Urbanization Risk = Flood Risk Score
```

Normalize the components and apply weights:

```text
risk_score = 
    0.35 * rainfall_component + 
    0.25 * drainage_component + 
    0.15 * elevation_component + 
    0.15 * impervious_component + 
    0.10 * historical_component
```

Multiply by 100. Make weights configurable.

---

## 9. Risk Classification

Map the score to:
- `0–25`   = LOW
- `26–50`  = MODERATE
- `51–75`  = HIGH
- `76–100` = CRITICAL

Return:
```json
{
  "area_id": "A001",
  "risk_score": 83,
  "risk_level": "CRITICAL"
}
```

---

## 10. Time-to-Flood Prediction

Create an MVP function estimating how soon an area may become waterlogged. A simple interpretable model is acceptable.

For example:
```text
drainage_capacity - current_rainfall
```
combined with historical vulnerability.

Return:
```json
{
  "time_to_flood_minutes": 32
}
```

The UI should display:
> **Flooding likely in ~32 min**

Add an interface note:
> Demo prediction based on modeled/simulated data.

---

## 11. Optional ML Model (AWS SageMaker Integration)

Structure the code so an ML model can replace the rule-based predictor.

Create an interface such as:
```python
class FloodPredictor:
    def predict(self, features):
        ...
```

Implement `RuleBasedFloodPredictor` first.

Also provide the architecture for `MLFloodPredictor` using RandomForest. In a real scenario, this would trigger an endpoint hosted on **Amazon SageMaker**.

If synthetic/demo data is used, explicitly label it as synthetic. Do not fabricate model accuracy.

---

## 12. Intervention Engine

This is a critical component. DrainMind must not stop at prediction.

Create an intervention simulator. Supported interventions:

- **Clear Drain**: `drain_capacity += 20–30%`
- **Deploy Pump**: `effective drainage capacity += configurable amount`
- **Restrict Traffic**: `urban runoff factor decreases slightly`
- **Emergency Warning**: Does not physically reduce flooding, but reduces exposure. Triggers **Amazon SNS**.
- **Open Water Storage**: Reduces runoff reaching the drainage network.

---

## 13. Intervention Simulation

For each selected intervention, recalculate:
- Flood Risk
- Time to Flood
- Estimated Flood Severity

Example return:
```json
{
  "before": {
    "risk_score": 84,
    "severity": 0.82,
    "time_to_flood_minutes": 32
  },
  "after": {
    "risk_score": 56,
    "severity": 0.31,
    "time_to_flood_minutes": 71
  },
  "impact": {
    "risk_reduction_pct": 33,
    "severity_reduction_pct": 62,
    "extra_warning_time_minutes": 39
  }
}
```

Clearly label this as a simulation.

---

## 14. Intervention Recommendation Logic

Implement a simple rules/recommendation engine:

```text
If rainfall is high AND drainage capacity is low:
    recommend "Clear Drain"

If rainfall is extreme AND risk is critical:
    recommend "Deploy Pump"

If critical location is near major road:
    recommend "Restrict Traffic"

If flood cannot be prevented:
    recommend "Issue Warning"
```

Return the top 1–3 interventions. Each recommendation should explain WHY.
> **Deploy Pump**: Drainage capacity is insufficient for predicted rainfall intensity.

---

## 15. Frontend Dashboard

Create a polished single-page dashboard hosted on **AWS Amplify**.

Header Display:
```text
DRAINMIND
Urban Flood Intelligence
System Status: ● Operational (AWS Cloud)
```

---

## 16. Main Map

The map should occupy the largest part of the screen. Show area markers/polygons.
Each area should visually communicate: low risk, moderate risk, high risk, critical risk.
Clicking an area opens its detail panel.

---

## 17. Right-Side Area Panel

When an area is selected:

```text
Central Market
Flood Risk: 83 / 100 [CRITICAL]
Predicted flooding: ~32 min
Rainfall: 72 mm/hr
Drain capacity: 45 mm/hr
```

### Risk Drivers
```text
High rainfall       ██████████
Poor drainage       ████████
Low elevation       ██████
Urban surface       ███████
Historical risk     ████████
```

---

## 18. Rainfall Simulator

Provide an obvious slider:
```text
Simulate Rainfall
[---------●------------]
Current: 62 mm/hr
```
As the slider changes, make an API call to the backend. The map and dashboard must update immediately.

---

## 19. Flood Forecast Timeline

Display a visual chart:
```text
NOW
│
├── +15 min   Moderate
├── +30 min   High
├── +45 min   Critical
└── +60 min   Severe
```

---

## 20. Intervention Simulator UI

Add a section:

```text
INTERVENTION SIMULATOR

Current predicted severity
████████████████░░ 82%

Choose intervention:
[ Clear Drain ] [ Deploy Pump ] [ Restrict Traffic ] [ Issue Warning ]

             ↓

Simulated severity
██████░░░░░░░░░░░ 31%

Estimated reduction: 62%
Additional warning time: +39 min
```

---

## 21. City-Level Overview

Add summary cards:
```text
HIGH-RISK AREAS: 7
CRITICAL AREAS: 2
NEXT FLOOD EVENT: 32 min
PEOPLE POTENTIALLY AFFECTED: 12,400
ESTIMATED RISK REDUCTION: 34%
```

---

## 22. Emergency Alert (Amazon SNS Integration)

When a location becomes critical, show an in-app alert:

> 🚨 **Flood Risk Alert**
> Central Market is expected to experience severe waterlogging within ~32 minutes.
> Recommended action: Clear drainage channel immediately.

*Hackathon Bonus*: Connect this to **Amazon SNS** so that when the user clicks "Issue Warning", it actually sends a real SMS to the judges' or your phone during the demo.

---

## 23. Backend APIs

Implement at minimum:
```text
GET /api/areas
GET /api/weather
GET /api/risk
GET /api/risk/{area_id}
GET /api/forecast/{area_id}
POST /api/simulate/rainfall
POST /api/intervention/simulate
GET /api/recommendations/{area_id}
GET /api/dashboard/summary
```
Return clean JSON. Serve via **Amazon API Gateway**.

---

## 24. Demo Data

Create realistic synthetic data for approximately 20–50 geographic areas.
Include coordinates, elevation, drainage capacity, and synthetic population.
Use deterministic random seeds so the demo is reproducible. Do NOT claim synthetic data is real.

---

## 25. Demo City

Use one fictional/demo city or a simplified representation of a real city. The application should support replacing the demo data with real datasets in Amazon RDS later.

---

## 26. Project Structure

Include AWS deployment configurations (like AWS SAM, Serverless Framework, or CDK):

```text
drainmind/
│
├── backend/
│   ├── app/ (FastAPI app)
│   ├── tests/
│   ├── requirements.txt
│   └── template.yaml (AWS SAM template for Lambda/API Gateway)
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── amplify.yml (AWS Amplify build settings)
│
├── scripts/
│   └── generate_demo_data.py
│
├── docker-compose.yml (For local testing)
└── README.md
```

---

## 27. UI/UX Requirements

The interface must look like a real climate-tech product, not a college CRUD application.
Prioritize clean typography, large map, minimal clutter, obvious emergency states, and responsive design. The user should understand the system within 10 seconds.

---

## 28. Important Hackathon Principle

Do not build:
> "AQI dashboard but for floods."

Build:
> **Prediction + explanation + intervention + measurable simulated impact + Cloud Scalability.**

The dashboard should always guide the user toward a decision.

---

## 29. Demo Script

### Step 1
Open DrainMind (Hosted on AWS Amplify). Show 7 high-risk areas, 2 critical areas.

### Step 2
Increase rainfall from 25 → 50 → 80 mm/hr. Watch the map dynamically change.

### Step 3
Select the most critical area. Show: **Flooding predicted in 32 minutes.**

### Step 4
Show why: `Rainfall > Drainage Capacity + Low Elevation...`

### Step 5
Ask: "What can we do?" DrainMind recommends: **Clear Drain** or **Issue Warning**.

### Step 6
Run intervention simulation.
Before: `Risk: 84 | Severity: 82% | Flood in: 32 min`
After: `Risk: 56 | Severity: 31% | Flood in: 71 min`

### Step 7
Trigger the "Issue Warning" intervention to send a live SMS to your phone via Amazon SNS. 
End with: **"39 additional minutes of warning. 62% lower simulated flood severity."**

---

## 30. Future Scope

Structure the code for future integration with:
- **AWS IoT Core**: for live street-level water sensors.
- **AWS Ground Station**: for live satellite weather imagery.
- Real rainfall APIs & drainage-network GIS.
- Reinforcement algorithms for pump optimizations.

---

## 31. Quality Requirements

The implementation must:
- Run locally (via Docker) AND be deployable to AWS.
- Have no placeholder buttons or broken routes.
- Include API documentation (Swagger via FastAPI).
- Validate inputs and handle missing data.

---

## 32. Deliverables

1. Complete backend (FastAPI ready for Lambda)
2. Complete frontend (React/Vite)
3. Demo dataset generator
4. Flood-risk prediction engine
5. Intervention simulator
6. Interactive map & dashboard
7. AWS Architecture Diagram
8. Deployment configurations (template.yaml, amplify.yml)
9. README with exact commands to run locally and deploy to AWS.

---

## 33. Final Product Positioning

The product tagline:
> **DrainMind — Predict the Flood. Prevent the Impact.**

The central product statement:
> DrainMind is an intelligent, cloud-native urban flood-response system that predicts hyperlocal waterlogging, explains the risk factors, and recommends interventions before streets become unusable.

Build the MVP around this single principle:
> **Every prediction must lead to an action.**