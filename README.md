# Lastbilsparkering nära dig

En liten Flask-app för Sverige som visar ett lokalt dataset med parkerings- och rastplatskandidater nära webbläsarens aktiva position utan API-nycklar. Kartan använder Leaflet och OpenStreetMap; datasetet hämtas från Overpass API.

## Starta

1. Installera beroenden:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

2. Starta lokalt:

   ```powershell
   python app.py
   ```

För produktionskörning:

```powershell
waitress-serve --host=127.0.0.1 --port=8080 app:app
```

3. Öppna `http://127.0.0.1:5000` och tillåt platsåtkomst.

Ingen API-nyckel behövs. `.env` är bara valfri konfiguration av Overpass-server, port och live-reserv. Live-reserven är avstängd som standard så en publik app inte kan belasta Overpass om den lokala datafilen saknas.

## Uppdatera platsdata

Nationella data ligger i `data/parking_sweden.json`. Uppdatera filen med:

```powershell
python download_places.py
```

Skriptet hämtar fyra geografiska delar av Sverige och söker efter `highway=rest_area`, `highway=services`, samt parkeringar med dokumenterad `hgv`, `truck` eller lastbils-/rastplatsmärkning. Den senaste hämtningen gav 957 platser, inklusive Rautas rastplatser. Appen sorterar lokala resultat efter dokumenterad lastbilsrelevans och avstånd och använder Overpass som reserv om datasetet saknas.

## Säkerhet och driftsäkerhet

- Backend använder timeout, validerar koordinater/radie och skickar en fast Overpass-fråga. Användaren kan inte påverka frågans filter eller injicera Overpass-syntax via URL-parametrarna.
- När `data/parking_sweden.json` finns används bara lokal data, även när sökningen ger noll träffar. Det förhindrar upprepade Overpass-anrop vid normal användning. `ALLOW_LIVE_FALLBACK` är avstängt som standard.
- GPS-positionen skickas i en POST-body i stället för URL:en, och API-svar använder `no-store`; appen sparar inte positioner lokalt.
- Flask accepterar högst 4 KiB request-body och appens egna loggar skriver inte request-body eller GPS-position. Waitress loggar normalt endast metod, sökväg och status; konfigurera även eventuell proxy utan body-loggning.
- Klienten använder `textContent` för platsdata och externa länkar öppnas med `noopener noreferrer`.
- OpenStreetMap-data kan vara ofullständig och Overpass-servrar har kapacitetsbegränsningar. Appen använder därför bara en begränsad radie och högst 20 resultat.
- `highway=rest_area` betyder rastplats, inte automatiskt att en lång lastbil får plats. Endast uttrycklig HGV-/truckmärkning ger lastbilsrelevans i resultatet.

## Begränsningar

OpenStreetMap-data kan föreslå lastbilsparkering och rastplatser men garanterar inte att ett visst fordon får plats. Kontrollera alltid aktuell skyltning, fri höjd, fordonslängd, vikt, öppettider och tillgänglighet.

## Källgranskning

Implementeringen använder [Leaflet 1.9.4](https://leafletjs.com/reference.html), [OpenStreetMap tile-servrar](https://operations.osmfoundation.org/policies/tiles/) och [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API). Källorna används via deras publika, dokumenterade gränssnitt; appen scrapar inte kartwebbplatser.

## Licenser och attribution

Källkoden i detta repository distribueras under MIT-licensen, se [LICENSE](LICENSE). Datasetet `data/parking_sweden.json` är bearbetat från OpenStreetMap och omfattas av [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/). Källa: [© OpenStreetMap contributors](https://www.openstreetmap.org/copyright), hämtat 2026-08-28. OSM-attribution ska finnas kvar när data eller appen distribueras.

Kör tester med:

```powershell
python -m pytest -q
```

## Belastningskontroll

En lokal kontroll mot den integrerade JSON-filen gav 100/100 lyckade svar vid 100 samtidiga klienter (p95 cirka 370 ms) och 200/200 lyckade svar vid 200 samtidiga klienter (p95 cirka 808 ms). Detta testar endast lokal utvecklingsserver och lokal data, inte publik drift eller Overpass. Använd inte Flask-utvecklingsservern på internet; använd en WSGI-server bakom HTTPS, rate limiting och övervakning.

Vid publik drift ska webbserverns åtkomstloggar konfigureras utan request-body och med minimerad URL-loggning. Appen skickar inte positionen i URL:en, men serveroperatören ansvarar fortfarande för sina loggar och sin lagring.
