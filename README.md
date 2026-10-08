# DrainMind

DrainMind is a hackathon MVP for exploring where urban waterlogging may occur, how soon it may start, and how simulated response actions could change the outcome.

The included city, Verdantia, is fictional. All 30 neighborhoods, populations, rainfall, drainage attributes, and predictions are deterministic synthetic demo data. The rule-based model is an explainable prototype, not a validated hydrological forecast. No live sensors are used. The default warning action is in-app only and sends no SMS.

## Run locally

Prerequisites: Node.js 20+, Python 3.12+, and npm.

In PowerShell, start the API in one terminal:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Start the dashboard in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. API health and interactive OpenAPI docs are available at <http://localhost:8000/health> and <http://localhost:8000/docs>.

Alternatively, run both services with Docker Compose:

```powershell
docker compose up --build
```

## Demo flow

1. Drag rainfall from 25 to 50 and then 80 mm/hr; district colors and risk metrics update from API responses.
2. Select a district to inspect its risk drivers, flood timing, forecast timeline, and ranked recommendations.
3. Choose a response action to compare modeled severity and warning time before and after.
4. “Issue warning” displays an in-app demo notice. It does not send a text message in this configuration.

The map is a local schematic district grid with fictional geometry and no external tile provider or map token.

## API

All routes return JSON. The `X-Simulation-Id` header scopes rainfall by browser session. Slider updates also carry a persisted `X-Simulation-Revision`; older delayed requests cannot overwrite newer scenarios in local memory or DynamoDB.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/areas` | Fictional district attributes |
| GET | `/api/weather` | Current synthetic weather observation |
| GET | `/api/risk` | Risk for every district |
| GET | `/api/risk/{area_id}` | Selected district risk and drivers |
| GET | `/api/forecast/{area_id}` | 60-minute modeled risk timeline |
| POST | `/api/simulate/rainfall` | Update scenario rainfall and recalculate risk |
| POST | `/api/intervention/simulate` | Compare modeled outcome for an action |
| GET | `/api/recommendations/{area_id}` | Ranked action recommendations with reasons |
| GET | `/api/dashboard/summary` | City-level risk and affected-population totals |

## Model notes

The configurable weights in `backend/app/engine.py` start at 0.35 rainfall, 0.25 drainage, 0.15 elevation, 0.15 impervious surface, and 0.10 historical vulnerability. Components are normalized to 0–1 and the weighted score is classified as LOW (0–25), MODERATE (26–50), HIGH (51–75), or CRITICAL (76–100). Time-to-flood is an interpretable heuristic based on rainfall versus drain capacity and vulnerability. Severity is derived from the score. These values are modeled outputs, not scientific estimates.

The `FloodPredictor` interface has both the active rule-based implementation and an optional `MLFloodPredictor` SageMaker Runtime adapter for a deployed RandomForest endpoint. Set `SAGEMAKER_ENDPOINT_NAME` to switch the API to that adapter. The endpoint must accept `{"features": {...}}` and return `risk_score` and `time_to_flood_minutes` (optional `severity` and `factors`). A RandomForest model must be trained on validated local event records; the synthetic sample data is not training evidence and no accuracy is claimed.

Interventions model drain capacity (+25%), pump capacity (+24 mm/hr), reduced impervious runoff (-8 percentage points), or reduced effective rainfall reaching drains (open storage). An emergency warning leaves physical severity unchanged and reports a separate illustrative exposure reduction. These are decision-support simulations, not operational instructions.

## AWS deployment preparation

The SAM template provisions API Gateway, Lambda, a DynamoDB table for per-session rainfall state, and an SNS topic. It sets `ALERT_MODE=local_demo`; it does not send notifications. AWS CLI and SAM CLI are required to deploy, and must be configured locally. No account IDs or credentials are embedded in this repository.

From the repository root:

```powershell
sam build --template-file backend/template.yaml
sam deploy --guided --template-file .aws-sam/build/template.yaml
```

After deployment, set the `ApiUrl` output as the Amplify app environment variable `VITE_API_URL` and update Lambda `CORS_ORIGINS` to the Amplify app origin before connecting the hosted UI. In Amplify, connect the repository, set the app root to `frontend`, and use `frontend/amplify.yml` for the build. This workspace has no AWS CLI/SAM installation and no AWS credentials were provided, so cloud resources have not been created.

To enable real SNS publishing later, configure a verified SNS topic subscription, set the deployed Lambda environment variable `ALERT_MODE=sns`, and retain `SNS_TOPIC_ARN` from the SAM output. The recipient phone number is managed by the SNS subscription, not hard-coded here.

## Checks

```powershell
cd backend
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

```powershell
cd frontend
npm run build
```