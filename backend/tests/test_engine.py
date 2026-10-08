import unittest
from io import BytesIO
import json

from app.engine import Area, MLFloodPredictor, RuleBasedFloodPredictor, simulate_intervention


class FakeSageMakerRuntime:
    def __init__(self):
        self.request = None

    def invoke_endpoint(self, **request):
        self.request = request
        return {"Body": BytesIO(json.dumps({"risk_score": 83, "time_to_flood_minutes": 32}).encode())}


class FloodEngineTests(unittest.TestCase):
    def setUp(self):
        self.area = Area("F-01", "Canal Quarter", 0, 0, 4, 35, 88, 0.35, 0.8, 12000, True)
        self.predictor = RuleBasedFloodPredictor()

    def test_rainfall_increases_risk_and_reduces_warning_time(self):
        dry = self.predictor.predict(self.area, 10)
        storm = self.predictor.predict(self.area, 80)
        self.assertGreater(storm.risk_score, dry.risk_score)
        self.assertLess(storm.time_to_flood_minutes, dry.time_to_flood_minutes)
        self.assertIn(storm.risk_level, {"LOW", "MODERATE", "HIGH", "CRITICAL"})

    def test_intervention_changes_hydraulic_simulation(self):
        result = simulate_intervention(self.predictor, self.area, 80, "deploy_pump")
        self.assertTrue(result["simulation_only"])
        self.assertLess(result["after"]["risk_score"], result["before"]["risk_score"])
        self.assertGreater(result["impact"]["extra_warning_time_minutes"], 0)

    def test_warning_does_not_claim_physical_flood_reduction(self):
        result = simulate_intervention(self.predictor, self.area, 80, "emergency_warning")
        self.assertEqual(result["before"]["risk_score"], result["after"]["risk_score"])
        self.assertEqual(result["impact"]["severity_reduction_pct"], 0)
        self.assertEqual(result["impact"]["exposure_reduction_pct"], 35)

    def test_sagemaker_adapter_maps_random_forest_response(self):
        runtime = FakeSageMakerRuntime()
        predictor = MLFloodPredictor("demo-random-forest", runtime)
        result = predictor.predict(self.area, 72)
        request = json.loads(runtime.request["Body"])
        self.assertEqual(runtime.request["EndpointName"], "demo-random-forest")
        self.assertEqual(request["features"]["rainfall_mm_hr"], 72)
        self.assertEqual(result.risk_level, "CRITICAL")
        self.assertEqual(result.time_to_flood_minutes, 32)


if __name__ == "__main__":
    unittest.main()