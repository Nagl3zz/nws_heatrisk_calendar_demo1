const stateSelect = document.getElementById("stateSelect");
const stationSelect = document.getElementById("stationSelect");
const yearSelect = document.getElementById("yearSelect");
const img = document.getElementById("calendarImg");
const caption = document.getElementById("caption");

const STATIONS = window.HEATRISK_STATIONS || [];
const AVG_YEAR = 2026;

function uniq(arr) { return [...new Set(arr)]; }

function fillStates() {
  const states = uniq(STATIONS.map(s => s.state).filter(Boolean)).sort();
  stateSelect.innerHTML = "";
  const allOpt = document.createElement("option");
  allOpt.value = "ALL";
  allOpt.textContent = "All states";
  stateSelect.appendChild(allOpt);

  for (const s of states) {
    const o = document.createElement("option");
    o.value = s;
    o.textContent = s;
    stateSelect.appendChild(o);
  }
}

function filteredStations() {
  const st = stateSelect.value || "ALL";
  return STATIONS
    .filter(s => st === "ALL" || s.state === st)
    .sort((a,b) => (a.name||a.id).localeCompare(b.name||b.id));
}

function fillStations() {
  stationSelect.innerHTML = "";
  const list = filteredStations();
  for (const s of list) {
    const o = document.createElement("option");
    o.value = s.id;
    o.textContent = `${s.name} (${s.id})`;
    stationSelect.appendChild(o);
  }
}

function fillYears() {
  yearSelect.innerHTML = "";
  const s = STATIONS.find(x => x.id === stationSelect.value) || filteredStations()[0];
  if (!s) return;

  for (const y of s.years) {
    const o = document.createElement("option");
    o.value = String(y);
    o.textContent = String(y);
    yearSelect.appendChild(o);
  }
  const avg = document.createElement("option");
  avg.value = "avg";
  avg.textContent = `Average (${AVG_YEAR})`;
  yearSelect.appendChild(avg);
}

function updateImage() {
  const stationId = stationSelect.value;
  const y = (yearSelect.value === "avg") ? String(AVG_YEAR) : yearSelect.value;
  img.src = `img/${stationId}_${y}.png`;
  const station = STATIONS.find(x => x.id === stationId);
  caption.textContent = station ? `${station.name} (${stationId}) — ${yearSelect.value}` : `${stationId} — ${yearSelect.value}`;
}

stateSelect.addEventListener("change", () => { fillStations(); fillYears(); updateImage(); });
stationSelect.addEventListener("change", () => { fillYears(); updateImage(); });
yearSelect.addEventListener("change", updateImage);

if (STATIONS.length) {
  fillStates(); fillStations(); fillYears(); updateImage();
} else {
  stateSelect.innerHTML = "<option>No stations yet — run the generator.</option>";
  caption.textContent = "Run python3 src/generate_calendars.py to generate stations.js and images.";
}
