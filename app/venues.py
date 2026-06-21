"""Catalogue of major Bengaluru event venues.

Real venues with real coordinates so the demo feels authentic. Each venue
carries a typical capacity which seeds the attendance defaults.
"""
from __future__ import annotations

from typing import Dict, List, Optional

VENUES: List[Dict] = [
    {
        "id": "chinnaswamy",
        "name": "M. Chinnaswamy Stadium",
        "type": "sports",
        "lat": 12.9788,
        "lon": 77.5996,
        "capacity": 40000,
        "note": "IPL / cricket -- CBD, surrounded by Cubbon Park & MG Road.",
    },
    {
        "id": "kanteerava",
        "name": "Sree Kanteerava Stadium",
        "type": "sports",
        "lat": 12.9626,
        "lon": 77.5946,
        "capacity": 24000,
        "note": "Football / athletics in the heart of the city.",
    },
    {
        "id": "palace_grounds",
        "name": "Bangalore Palace Grounds",
        "type": "concert",
        "lat": 13.0010,
        "lon": 77.5920,
        "capacity": 35000,
        "note": "Concerts & exhibitions, Bellary Road corridor.",
    },
    {
        "id": "biec",
        "name": "BIEC Exhibition Centre",
        "type": "exhibition",
        "lat": 13.0640,
        "lon": 77.4790,
        "capacity": 30000,
        "note": "Trade fairs on Tumkur Road / NH-4.",
    },
    {
        "id": "kanteerava_indoor",
        "name": "Kanteerava Indoor Arena",
        "type": "concert",
        "lat": 12.9633,
        "lon": 77.5925,
        "capacity": 12000,
        "note": "Indoor concerts & indoor sports.",
    },
    {
        "id": "freedom_park",
        "name": "Freedom Park",
        "type": "rally",
        "lat": 12.9789,
        "lon": 77.5810,
        "capacity": 25000,
        "note": "Political rallies & public gatherings.",
    },
    {
        "id": "national_college",
        "name": "National College Grounds",
        "type": "festival",
        "lat": 12.9430,
        "lon": 77.5730,
        "capacity": 20000,
        "note": "Festivals & cultural events, Basavanagudi.",
    },
    {
        "id": "nice_road_marathon",
        "name": "Cubbon Park (Marathon Start)",
        "type": "marathon",
        "lat": 12.9763,
        "lon": 77.5929,
        "capacity": 15000,
        "note": "Marathon start/finish in central Bengaluru.",
    },
]

_BY_ID = {v["id"]: v for v in VENUES}


def get_venue(venue_id: str) -> Optional[Dict]:
    return _BY_ID.get(venue_id)
