import math
import os
from pathlib import Path
import json
from typing import Any

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024

OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
ALLOW_LIVE_FALLBACK = os.getenv("ALLOW_LIVE_FALLBACK", "false").lower() == "true"
DATA_PATH = Path(__file__).parent / "data" / "parking_sweden.json"
MAX_RADIUS_METERS = 150_000
DEFAULT_RADIUS_METERS = 10_000


@app.after_request
def prevent_location_caching(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "geolocation=(self)"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
        "script-src 'self' https://unpkg.com; "
        "style-src 'self' https://unpkg.com 'unsafe-inline'; "
        "img-src 'self' data: blob: https://*.tile.openstreetmap.org https://unpkg.com; "
        "connect-src 'self' https://overpass-api.de"
    )
    return response


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error": "Förfrågan är för stor."}), 413


def _as_float(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} måste vara ett tal") from error
    if not math.isfinite(number):
        raise ValueError(f"{name} måste vara ett ändligt tal")
    if not (-180 <= number <= 180):
        raise ValueError(f"{name} ligger utanför tillåtet intervall")
    return number


def _distance_meters(latitude: float, longitude: float, place_latitude: float, place_longitude: float) -> float:
    earth_radius = 6_371_000
    latitude_delta = math.radians(place_latitude - latitude)
    longitude_delta = math.radians(place_longitude - longitude)
    origin_latitude = math.radians(latitude)
    target_latitude = math.radians(place_latitude)
    haversine = (math.sin(latitude_delta / 2) ** 2
                 + math.sin(longitude_delta / 2) ** 2
                 * math.cos(origin_latitude) * math.cos(target_latitude))
    return earth_radius * 2 * math.asin(math.sqrt(haversine))


def _nearby_local_places(latitude: float, longitude: float, radius: int) -> list[dict[str, Any]]:
    if not DATA_PATH.exists():
        return []
    with DATA_PATH.open(encoding="utf-8") as data_file:
        places = json.load(data_file)
    nearby = []
    for place in places:
        distance = _distance_meters(latitude, longitude, place["latitude"], place["longitude"])
        if distance <= radius:
            nearby.append({**place, "distanceMeters": round(distance)})
    return sorted(nearby, key=lambda place: (not place["truckRelevant"], place["distanceMeters"]))[:20]


def _search_places(latitude: float, longitude: float, radius: int) -> list[dict[str, Any]]:
    if DATA_PATH.exists():
        return _nearby_local_places(latitude, longitude, radius)
    if not ALLOW_LIVE_FALLBACK:
        return []

    query = f"""
[out:json][timeout:20];
(
  nwr(around:{radius},{latitude},{longitude})["amenity"="parking"];
  nwr(around:{radius},{latitude},{longitude})["highway"="rest_area"];
  nwr(around:{radius},{latitude},{longitude})["amenity"="parking_space"]["hgv"];
);
out center tags;
"""
    headers = {
        "Accept": "application/json",
        "User-Agent": "lastbilsparkering-sverige/1.0 (lokal app)",
    }
    response = requests.post(OVERPASS_URL, data=query, headers=headers, timeout=25)
    response.raise_for_status()
    places = []
    for place in response.json().get("elements", []):
        tags = place.get("tags", {})
        center = place.get("center", place)
        place_latitude = center.get("lat")
        place_longitude = center.get("lon")
        if place_latitude is None or place_longitude is None:
            continue
        name = tags.get("name") or tags.get("operator") or "Parkering / rastplats"
        searchable_tags = " ".join([
            tags.get("hgv", ""), tags.get("truck", ""), tags.get("name", ""),
            tags.get("description", ""), tags.get("access", ""),
        ]).lower()
        truck_relevant = any(value in searchable_tags for value in (
            "yes", "designated", "lastbil", "truck", "hgv",
        ))
        places.append({
            "id": f"{place.get('type')}-{place.get('id')}",
            "name": name,
            "address": tags.get("addr:street") or tags.get("ref") or "Sverige",
            "latitude": place_latitude,
            "longitude": place_longitude,
            "distanceMeters": round(_distance_meters(latitude, longitude, place_latitude, place_longitude)),
            "truckRelevant": truck_relevant,
            "mapsUrl": f"https://www.openstreetmap.org/{place.get('type')}/{place.get('id')}",
        })
    return sorted(places, key=lambda place: (not place["truckRelevant"], place["distanceMeters"]))[:20]


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/search")
def search():
    try:
        payload = request.get_json(silent=True) or {}
        latitude = _as_float(payload.get("lat"), "lat")
        longitude = _as_float(payload.get("lng"), "lng")
        radius = int(payload.get("radius", DEFAULT_RADIUS_METERS))
        if not (-90 <= latitude <= 90):
            raise ValueError("lat ligger utanför tillåtet intervall")
        if not (0 < radius <= MAX_RADIUS_METERS):
            raise ValueError("radie måste vara mellan 1 och 150 000 meter")
        return jsonify({"places": _search_places(latitude, longitude, radius)})
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except requests.RequestException:
        app.logger.exception("Overpass-anropet misslyckades")
        return jsonify({"error": "Kunde inte hämta platser från OpenStreetMap just nu."}), 502


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
