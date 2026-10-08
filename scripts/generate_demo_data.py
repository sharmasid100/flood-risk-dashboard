import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.demo_data import CITY_NAME, DATA_LABEL, generate_areas

print(json.dumps({"city": CITY_NAME, "data_label": DATA_LABEL, "areas": [asdict(area) for area in generate_areas()]}, indent=2))