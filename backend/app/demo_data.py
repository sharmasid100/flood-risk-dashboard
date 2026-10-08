from __future__ import annotations

import random

from .engine import Area


CITY_NAME = "Verdantia"
DATA_LABEL = "Synthetic demonstration data"
AREA_NAMES = [
    "Canal Quarter", "Old Foundry", "Willow Basin", "East Market", "Civic Steps",
    "Glassworks", "South Garden", "Mariner's Row", "Copperfield", "Orchard Gate",
    "North Exchange", "Paper Mill", "Lowbridge", "Juniper Park", "West Reservoir",
    "Lantern Ward", "Railway Flats", "Mossbank", "Riverbend", "Stone Arcade",
    "Tide Court", "Meadowline", "Founders' Square", "Ashgrove", "Harbor Walk",
    "Rainwell", "Millstone", "Cedar Loop", "South Crossing", "Beacon Hill",
]


def generate_areas() -> list[Area]:
    rng = random.Random(20261008)
    areas = []
    for index, name in enumerate(AREA_NAMES):
        cluster = index % 5
        column = index // 5
        areas.append(
            Area(
                area_id=f"V-{index + 1:03d}",
                name=name,
                x=150 + cluster * 160 + rng.uniform(-32, 32),
                y=140 + column * 135 + rng.uniform(-28, 28),
                elevation_m=round(rng.uniform(2.5, 22), 1),
                drain_capacity_mm_hr=round(rng.uniform(28, 78), 1),
                impervious_surface_pct=round(rng.uniform(42, 94), 1),
                drainage_score=round(rng.uniform(0.28, 0.88), 2),
                historical_flood_frequency=round(rng.uniform(0.14, 0.86), 2),
                population=rng.randrange(1800, 16600, 100),
                near_major_road=index % 3 == 0 or index in {7, 18, 26},
            )
        )
    return areas