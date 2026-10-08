import unittest

from fastapi.testclient import TestClient

from app.main import app


class FloodApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.session = {"X-Simulation-Id": "api-test-session"}

    def test_area_and_summary_contracts_use_labeled_synthetic_data(self):
        areas = self.client.get("/api/areas").json()
        summary = self.client.get("/api/dashboard/summary", headers=self.session).json()
        self.assertEqual(len(areas["areas"]), 30)
        self.assertIn("Synthetic", areas["data_label"])
        self.assertEqual(summary["area_count"], 30)
        self.assertIsNone(summary["next_event"])

    def test_rainfall_isolated_by_simulation_id_and_drives_forecast(self):
        response = self.client.post("/api/simulate/rainfall", headers=self.session, json={"rainfall_mm_hr": 80})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["rainfall_mm_hr"], 80)
        self.assertIsNotNone(self.client.get("/api/dashboard/summary", headers=self.session).json()["next_event"])
        own_weather = self.client.get("/api/weather", headers=self.session).json()
        other_weather = self.client.get("/api/weather", headers={"X-Simulation-Id": "other-session"}).json()
        self.assertEqual(own_weather["rainfall_mm_hr"], 80)
        self.assertEqual(other_weather["rainfall_mm_hr"], 25)
        area_id = response.json()["areas"][0]["area_id"]
        forecast = self.client.get(f"/api/forecast/{area_id}", headers=self.session).json()["forecast"]
        self.assertEqual(len(forecast), 5)
        self.assertEqual(forecast[0]["rainfall_mm_hr"], 80)

    def test_newer_rainfall_revision_wins_over_late_old_write(self):
        newer = {**self.session, "X-Simulation-Revision": "2"}
        older = {**self.session, "X-Simulation-Revision": "1"}
        self.client.post("/api/simulate/rainfall", headers=newer, json={"rainfall_mm_hr": 80})
        self.client.post("/api/simulate/rainfall", headers=older, json={"rainfall_mm_hr": 10})
        weather = self.client.get("/api/weather", headers=self.session).json()
        self.assertEqual(weather["rainfall_mm_hr"], 80)

    def test_warning_route_is_explicitly_local_demo(self):
        response = self.client.post("/api/intervention/simulate", headers=self.session, json={
            "area_id": "V-001",
            "intervention": "emergency_warning",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["notification"]["sent"])
        self.assertEqual(response.json()["notification"]["mode"], "local_demo")


if __name__ == "__main__":
    unittest.main()