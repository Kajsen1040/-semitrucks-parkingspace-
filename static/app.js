let map;
let userMarker;
let markers = [];
let activePosition;

const statusElement = document.querySelector("#status");
const resultsElement = document.querySelector("#results");
const radiusElement = document.querySelector("#radius");

function setStatus(message, isError = false) {
  statusElement.textContent = message;
  statusElement.classList.toggle("error", isError);
}

function showResults(places) {
  resultsElement.replaceChildren();
  if (!places.length) {
    resultsElement.textContent = "Inga kandidater hittades inom vald radie.";
    return;
  }
  places.forEach((place, index) => {
    const item = document.createElement("article");
    item.className = "result";
    const title = document.createElement("h2");
    title.textContent = `${index + 1}. ${place.name}`;
    const address = document.createElement("p");
    address.textContent = place.address;
    const link = document.createElement("a");
    link.href = place.mapsUrl;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Öppna i OpenStreetMap";
    const distance = document.createElement("p");
    distance.textContent = `${(place.distanceMeters / 1000).toFixed(1)} km bort${place.truckRelevant ? " · lastbilsrelevant märkning" : " · parkering/rastplats"}`;
    item.append(title, address, distance, link);
    item.addEventListener("click", () => map.panTo([place.latitude, place.longitude]));
    resultsElement.appendChild(item);
  });
}

async function searchPlaces() {
  if (!activePosition) return;
  setStatus("Söker nära dig ...");
  const { latitude, longitude } = activePosition.coords;
  const url = "/api/search";
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ lat: latitude, lng: longitude, radius: Number(radiusElement.value) }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Sökningen misslyckades");
    markers.forEach((marker) => map.removeLayer(marker));
    markers = data.places.map((place, index) => {
      const marker = L.marker([place.latitude, place.longitude], { title: place.name }).addTo(map);
      const popup = document.createElement("strong");
      popup.textContent = `${index + 1}. ${place.name}`;
      marker.bindPopup(popup);
      marker.on("click", () => map.panTo([place.latitude, place.longitude]));
      return marker;
    });
    showResults(data.places);
    setStatus(`${data.places.length} kandidater hittades`);
  } catch (error) {
    setStatus(error.message, true);
    resultsElement.textContent = "Sökningen kunde inte slutföras.";
  }
}

function onLocation(position) {
  activePosition = position;
  const center = { lat: position.coords.latitude, lng: position.coords.longitude };
  map.setView(center, 12);
  if (userMarker) userMarker.setLatLng(center);
  else userMarker = L.marker(center, { title: "Din position" }).addTo(map).bindPopup("Din position");
  searchPlaces();
}

function locate() {
  if (!navigator.geolocation) {
    setStatus("Webbläsaren stöder inte positionering.", true);
    return;
  }
  setStatus("Begär position ...");
  navigator.geolocation.getCurrentPosition(onLocation, () => {
    setStatus("Position nekades. Tillåt platsåtkomst och försök igen.", true);
  }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 });
}

function initMap() {
  map = L.map("map").setView([62.0, 15.0], 5);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap-bidragsgivare",
  }).addTo(map);
  radiusElement.addEventListener("change", searchPlaces);
  document.querySelector("#locate").addEventListener("click", locate);
  locate();
}

initMap();
