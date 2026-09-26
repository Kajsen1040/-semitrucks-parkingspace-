import json
import math
import os
from pathlib import Path

import requests

OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
OUTPUT_PATH = Path(__file__).parent / "data" / "parking_sweden.json"
BBOXES = (
    (55.0, 10.0, 59.5, 24.5),
    (59.5, 10.0, 63.0, 24.5),
    (63.0, 10.0, 66.0, 24.5),
    (66.0, 10.0, 69.5, 24.5),
)


def distance_meters(latitude, longitude, place_latitude, place_longitude):
    earth_radius = 6_371_000
    latitude_delta = math.radians(place_latitude - latitude)
    longitude_delta = math.radians(place_longitude - longitude)
    origin_latitude = math.radians(latitude)
    target_latitude = math.radians(place_latitude)
    haversine = (math.sin(latitude_delta / 2) ** 2
                 + math.sin(longitude_delta / 2) ** 2
                 * math.cos(origin_latitude) * math.cos(target_latitude))
    return earth_radius * 2 * math.asin(math.sqrt(haversine))


def main():
    output = []
    seen = set()
    headers = {"Accept": "application/json", "User-Agent": "lastbilsparkering-sverige/1.0"}
    for south, west, north, east in BBOXES:
        query = f"""
[out:json][timeout:60];
(
  nwr({south},{west},{north},{east})["highway"~"^(rest_area|services)$"];
  nwr({south},{west},{north},{east})["amenity"="parking"]["hgv"~"^(yes|designated|destination)$",i];
  nwr({south},{west},{north},{east})["amenity"="parking"]["truck"~"^(yes|designated)$",i];
  nwr({south},{west},{north},{east})["amenity"="parking"]["name"~"(lastbil|truck|rastplats)",i];
);
out center tags;
"""
        print(f"Hämtar Sverige-del {south}-{north} ...", flush=True)
        response = requests.post(OVERPASS_URL, data=query, headers=headers, timeout=90)
        response.raise_for_status()
        for place in response.json().get("elements", []):
            tags = place.get("tags", {})
            center = place.get("center", place)
            latitude = center.get("lat")
            longitude = center.get("lon")
            if latitude is None or longitude is None:
                continue
            identifier = f"{place.get('type')}-{place.get('id')}"
            if identifier in seen:
                continue
            seen.add(identifier)
            searchable_tags = " ".join([
                tags.get("hgv", ""), tags.get("truck", ""), tags.get("name", ""),
                tags.get("description", ""), tags.get("highway", ""),
            ]).lower()
            output.append({
                "id": identifier,
                "name": tags.get("name") or tags.get("operator") or "Parkering / rastplats",
                "address": tags.get("addr:street") or tags.get("ref") or "Sverige",
                "latitude": latitude,
                "longitude": longitude,
                "truckRelevant": any(value in searchable_tags for value in (
                    "yes", "designated", "lastbil", "truck", "hgv",
                )),
                "mapsUrl": f"https://www.openstreetmap.org/{place.get('type')}/{place.get('id')}",
            })
    output.sort(key=lambda place: (not place["truckRelevant"], place["name"]))
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Sparade {len(output)} platser i {OUTPUT_PATH}")


if __name__ == "__main__":
    main()